import pandas as pd 
import MySQLdb 
import datetime 
import calendar 
from dateutil import parser
from gitutils.utils import err
import getpass
import os

class Fetcher:
    def __init__(self, project_name):
        # Moved database code out of constructor (Google best practice on "doing work in constructor")
        # TODO: use project URL when possible since we will have multiple forks with the same project name, but different URLs
        self.project = project_name
        self.db = None
        self.cursor = None
        self.commit_data = None

    def fetch(self, db=None, cache=True):

        if cache and os.path.exists('.%s.pickle' % self.project):
            self.commit_data = pd.read_pickle('.%s.pickle'%self.project)
            return
        db_pwd = getpass.getpass(prompt='Database password:')
        if not db:
            self.db = MySQLdb.connect(host='sansa.cs.uoregon.edu', port=3331, user='ideas_user', passwd=db_pwd,
                                      db='ideas_db', charset='utf8')
        else:
            self.db = db
        self.cursor = self.db.cursor()

        # First, get a list of all projects
        comm_ans = self.cursor.execute('select name from project')
        projects = [x[0] for x in self.cursor.fetchall()]  # list of pairs, project name is first item in each pair
        if self.project not in projects:
            self.close_session()
            err("This project was not found in the database. Available projects are: %s" % str(projects))

        # TODO: eventually add d.language, a.email, and project url (to identify forks) to select
        commit_query =\
        '''select c.id as commit_id, c.hash as sha, c.branch as branch, c.datetime as datetime, 
            a.username as author, a.email as email, c.message as message, d.file_path, d.body 
        from commit c join author a on(c.author_id = a.id) 
            join project p on(c.project_id = p.id) join diff d on(c.id = d.commit_id)
        where p.name = %s'''
        comm_ans                 = self.cursor.execute(commit_query,
                                                       (self.project, ))
        self.commit_data         = pd.DataFrame(self.cursor.fetchall()) 
        self.commit_data.columns = ['index', 'sha', 'branch', 'datetime', 'author', 'email', 'message', 'filepath',
                                    'diff']
        self.commit_data.drop(columns=['index'])
        temp_d = self.commit_data['datetime'].map(lambda x: x.date())
        self.commit_data[['year', 'month', 'day', 'doy', 'dow']] = pd.DataFrame(
            list(
                temp_d.map(
                    lambda x : [x.year, x.month, x.day, x.timetuple().tm_yday, calendar.day_name[x.weekday()]]
                )
            )
            , index = self.commit_data.index 
        )
        if cache and not os.path.exists('.%s.pickle'%self.project):
            self.commit_data.to_pickle('.%s.pickle'%self.project)
        return



    def close_session(self):
        if self.cursor:
            self.cursor.close()
        if self.db:
            self.db.close()