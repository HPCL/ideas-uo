import atexit
import datetime
import logging
import os
import shutil
from urllib.parse import urlparse

import MySQLdb

from GitCommand import GitCommand

# Setup Logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(level=logging.DEBUG)
formatter = logging.Formatter(fmt="[%(levelname)s]: %(asctime)s - %(message)s")
ch.setFormatter(fmt=formatter)
logger.addHandler(hdlr=ch)

FORCE_EPOCH = True # if true checks from utc epoch

class DatabaseInterface:

    def __init__(self, host='127.0.0.1', port=3306, user='root', passwd='admin', db='djangostack'):
        try:
            self.db = MySQLdb.connect(host=host, port=port, user=user, passwd=passwd, db=db)
        except:
            logger.critical('Could not establish a connection to the database.')
            raise ConnectionError('Could not establish a connection to the database.')

        atexit.register(self.terminate)
        logger.debug('Established MySQL connection.')

    def terminate(self):
        self.db.close()
        logger.debug('Closed MySQL connection.')

    def get_git_name(self, url):
            name = urlparse(url)
            name = os.path.basename(name.path)
            name = name[:name.index('.')]
            return name

    def add_project(self, url, name=None, since=datetime.datetime.utcfromtimestamp(0).isoformat(), fork_of=None):
        '''
            url: url to git file
            name: descriptive name of project, defaults to .git file name
            since: ISO8601 datetime of when to grab git data from, defaults to utc epoch
            fork_of: url of git_project that it is a fork of, defaults None
        '''

        if not name:
            name = self.get_git_name(url)

        cursor = self.db.cursor()
        query = 'select count(*) from project where source_url=%s'
        cursor.execute(query, (url,))
        exists = cursor.fetchone()[0] == 1

        if exists:
            logger.debug('Found existing git project.')
            new_project = False

            # Update existing project
            query = 'select id from project where source_url=%s'
            cursor.execute(query, (url,))
            project_id = cursor.fetchone()[0]
            query = 'update project set last_updated=utc_timestamp() where id=%s'
            cursor.execute(query, (project_id,))
        else:
            logger.debug('Unknown git project.')
            new_project = True

            # If fork, find parent project_id
            if fork_of:
                #TODO: Currently assumes parent project already exists -- throw error otherwise?
                query = 'select id from project where source_url=%s'
                cursor.execute(query, (fork_of,))
                fork_of = cursor.fetchone()[0]

            # Insert new project
            query = 'insert into project (name, source_url, last_updated, fork_of_id) values (%s, %s, utc_timestamp(), %s)'
            cursor.execute(query, (name, url, fork_of,))

        self.db.commit()

        if FORCE_EPOCH:
            logger.debug('FORCE_EPOCH set to True.')

        # If new project grab everything, otherwise grab utc epoch
        if new_project or FORCE_EPOCH:
            since = datetime.datetime.utcfromtimestamp(0).isoformat()
            logger.debug(f'New project, grabbing all commit data since {since}.')
        else:
            # Find last time updated
            query = 'select last_updated from project where source_url=%s'
            cursor.execute(query, (url,))
            since = cursor.fetchone()[0]
            logger.debug(f'Existing project, grabbing all commit data since {since}.')

        cursor.close()

        self.process_project(url, since=since)

        if exists:
            logger.debug(f'Project from {url} updated.')
        else:
            logger.debug(f'New project from {url} inserted.')

    def process_project(self, url, since):
        name = self.get_git_name(url)

        # Cloned repo
        project = GitCommand('.')
        project.cloneRepo(url)
        data = project.getRepoCommitData('.', since=since)
        logger.debug(f'Cloned repository "{name}".')

        cursor = self.db.cursor()

        # Get project id
        query = 'select id from project where source_url=%s'
        cursor.execute(query, (url,))
        project_id = cursor.fetchone()[0]

        # Insert authors
        for author in data.keys():
            entry = author.decode('utf-8')
            username = entry[:entry.index('<') - 1]
            email = entry[entry.index('<') + 1:-1]

            query = 'select count(*) from author where username=%s and email=%s'
            cursor.execute(query, (username, email,))
            exists = cursor.fetchone()[0] == 1
            if not exists:
                query = 'insert into author (username, email) values (%s, %s)'
                cursor.execute(query, (username, email,))
                self.db.commit()

                logger.debug(f'Inserted new author {username}.')

            # Get author id
            query = 'select id from author where username=%s and email=%s'
            cursor.execute(query, (username, email,))
            author_id = cursor.fetchone()[0]

            # Update bridge table
            query = 'select count(*) from project_has_author where author_id=%s and project_id=%s'
            cursor.execute(query, (author_id, project_id,))
            exists = cursor.fetchone()[0] == 1
            if not exists:
                query = 'insert into project_has_author (author_id, project_id) values (%s, %s)'
                cursor.execute(query, (author_id, project_id,))
                self.db.commit()

                logger.debug(f'Inserted author {author_id} works on project {project_id}')

            # Insert commits
            for commit in data[author]['commits']:
                hash = commit['id']

                query = 'select count(*) from commit where hash=%s'
                cursor.execute(query, (hash,))
                exists = cursor.fetchone()[0] == 1
                # Skip existing commits
                if exists:
                    logger.debug(f'Commit {hash} already exists.')
                    continue

                date = commit['date'].decode('utf-8')
                dt = datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S%z').strftime('%Y-%m-%d %H:%M:%S')
                message = commit['message'].strip()
                branches = commit['branches']
                logger.critical(f'KEYS: {commit.keys()}')
                logger.critical(f'BRANCHES: {branches}')
                query = f'insert into commit (hash, datetime, author_id, project_id, message, branch) values (%s, %s, %s, %s, %s, %s)'

                cursor.execute(query, (hash, dt, author_id, project_id, message, branches,))
                self.db.commit()

                logger.debug(f'Inserted new commit {hash}.')

                # Get commit id
                query = 'select id from commit where hash=%s'
                cursor.execute(query, (hash,))
                commit_id = cursor.fetchone()[0]

                # Insert diffs
                for diff in commit['diffs']:
                    body = '\n'.join(diff['diff'])

                    filename = diff['filename']
                    filename = filename[filename.index('/'):filename.index(' ')][1:]

                    # TODO: Source analysis - programming language
                    language = 'PLACEHOLDER'
                    query = f'insert into diff (file_path, language, commit_id, body) values (%s, %s, %s, %s)'
                    cursor.execute(query, (filename, language, commit_id, body,))
                    self.db.commit()

                    logger.debug(f'Inserted diff in file {filename} for commit {hash}')

        # Remove cloned repo
        os.chdir('..')
        shutil.rmtree(f'./{name}/')
        logger.debug(f'Removed repository {name}')
        cursor.close()

if __name__ == '__main__':
    interface = DatabaseInterface()
    #url = 'https://github.com/spotify/dockerfile-maven.git'
    #url = 'https://github.com/google/gvisor.git' #- StopIteration line 108 GitCommand.py
    #url = 'https://github.com/petsc/petsc.git' #- Killed
    #url = 'https://github.com/HPCL/p2z-tests.git'
    #url = 'https://github.com/fickas/ideas-uo.git'
    #fork_of = 'https://github.com/HPCL/ideas-uo.git'
    url = 'https://github.com/HPCL/ideas-uo.git'
    #url = 'https://github.com/HPCL/autoperf.git'
    #url = 'https://github.com/HPCL/SLiM.git'
    #url = 'https://github.com/HPCL/easy-parallel-graph.git'
    fork_of = None
    interface.add_project(url, fork_of=fork_of)
