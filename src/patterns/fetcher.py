import pandas as pd 
import MySQLdb 
import datetime 
import calendar 
from dateutil import parser
from gitutils.utils import err
import getpass
import os
from os.path import abspath, dirname 
import glob

class Fetcher:

    def __init__(self, project_name, project_url = None, exclude_forks=False, forks_only=False):
        # Moved database code out of constructor (Google best practice on "doing work in constructor")
        # TODO: use project URL when possible since we will have multiple forks with the same project name, but different URLs
        self.project = project_name
        self.db = None
        self.cursor = None
        self.commit_data = None
        self.all_projects = None
        self.project_url = project_url  # Mainly used to indicate specific forks
        self.exclude_forks = exclude_forks # Only work with non-forks of the repo
        self.forks_only = forks_only  # when True, only analyze forked repos
        self.top_dir = abspath(dirname(dirname(dirname(__file__))))
        self.create_cache()

    def find_cache(self):
        for root, dirnames, filenames in os.walk(self.top_dir):
            filenames = [f for f in filenames if f == '.%s.pickle' % self.project]
            for filename in filenames:
                return os.path.join(root, filename)

    def fetch(self, db=None, cache=True, dbpwd=None):
        if cache:
            the_cache = self.find_cache()
            if the_cache:
                self.commit_data = pd.read_pickle(the_cache)
                self.commit_data.index = self.commit_data['datetime']  # DO NOT TOUCH THIS LINE!!
                print("INFO: Loaded local cached copy of %s data." % self.project)
                return True

        # Do not save the database password in publicly visible files, e.g, scripts, notebooks, etc!
        if dbpwd: db_pwd = dbpwd
        else: db_pwd = getpass.getpass(prompt='Database password:')
        if not db:
            self.db = MySQLdb.connect(host='sansa.cs.uoregon.edu', port=3331, user='ideas_user', passwd=db_pwd,
                                      db='ideas_db', charset='utf8')
        else:
            self.db = db
        self.cursor = self.db.cursor()
        print("INFO: Loading %s data from database. This can take a while..." % self.project)
        if self.project_url:
            _ = self.cursor.execute('select source_url from project')
            all_project_urls = [x[0] for x in self.cursor.fetchall()]  # list of pairs, project url is first item
            if self.project_url not in all_project_urls:
                self.close_session()
                err("This project URL was not found in the database. Available URLs are: %s" % '\n'.join(all_project_urls))
            else:
                _ = self.cursor.execute('select name from project where source_url = "%s"' % self.project_url)
                self.project = self.cursor.fetchall()[0][0]

        if not self.project_url:
            # First a list of all projects
            comm_ans = self.cursor.execute('select name from project')
            self.all_projects = [x[0] for x in self.cursor.fetchall()]  # list of pairs, project name is first item in each
            # pair
            if self.project not in self.all_projects:
                self.close_session()
                err("This project was not found in the database. Available projects are: %s" % ', '.join(self.all_projects))
            if not self.project and not self.project_url: return self.all_projects

        # TODO: eventually add d.language, a.email, and project url (to identify forks) to select
        commit_query =\
        '''select c.id as commit_id, c.hash as sha, c.branch as branch, c.datetime as datetime, 
            a.username as author, a.email as email, c.message as message, d.file_path, d.body 
        from commit c join author a on(c.author_id = a.id) 
            join project p on(c.project_id = p.id) join diff d on(c.id = d.commit_id) '''
        if self.project_url is None:
            commit_query += ' where p.name = "%s"' % self.project
            if self.exclude_forks: commit_query += ' and p.fork_of_id is null'
            elif self.forks_only: commit_query += ' and p.child_of_id is null'
        else:
            commit_query += 'where p.source_url = "%s" ' % self.project_url
        comm_ans = self.cursor.execute(commit_query)
        self.commit_data = pd.DataFrame(self.cursor.fetchall())
        self.commit_data.columns = ['index', 'sha', 'branch', 'datetime', 'author', 'email', 'message', 'filepath',
                                    'diff']
        self.commit_data.index = self.commit_data['datetime']
        temp_d = self.commit_data['datetime'].map(lambda x: x.date())
        self.commit_data[['year', 'month', 'day', 'doy', 'dow']] = pd.DataFrame(
            list(
                temp_d.map(
                    lambda x : [x.year, x.month, x.day, x.timetuple().tm_yday, calendar.day_name[x.weekday()]]
                )
            )
            , index = self.commit_data.index
        )
        self.commit_data = self.commit_data.drop(columns=['index'])   # datetime, too?

        cache_file = os.path.join(self.top_dir,'.db-cache', '.%s.pickle' % self.project)
        if not os.path.exists(cache_file):
            # Cache local copy
            self.commit_data.to_pickle(cache_file)
        info_msg = "INFO: Loaded %s data from the database (" % self.project
        if self.project_url:
            info_msg += 'url: ' + self.project_url + ', '
        info_msg += 'exclude_forks=%s, forks_only=%s)' % (str(self.exclude_forks), str(self.forks_only))
        print(info_msg)
        return True

    def create_cache(self):
        if not os.path.exists(self.cache_dir): os.mkdir(self.cache_dir)

    @property
    def cache_dir(self):
        return os.path.join(self.top_dir,'.db-cache')

    def update_cache(self):
        self.commit_data.to_pickle(os.path.join(self.cache_dir, '.%s.pickle' % self.project))

    def close_session(self):
        if self.cursor:
            self.cursor.close()
        if self.db:
            self.db.close()
