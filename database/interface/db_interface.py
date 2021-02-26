#!/usr/bin/env python3

import argparse
import atexit
import datetime
import logging
import os
import shutil
from urllib.parse import urlparse

import arrow
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

class DatabaseInterface:

    def __init__(self, args):
        self.args = args

        try:
            self.db = MySQLdb.connect(host=self.args.host, port=self.args.port, user=self.args.username, password=self.args.password, database=self.args.database, use_unicode=True, charset='utf8mb4')
        except:
            logger.critical('Could not establish a connection to the database.')
            raise ConnectionError('Could not establish a connection to the database.')

        atexit.register(self.terminate)
        logger.debug('Established MySQL connection.')

        if self.args.update:
            logger.debug('Updating existing projects on database...')
            cursor = self.db.cursor()
            query = 'select source_url from project'
            cursor.execute(query)
            projects = cursor.fetchall()
            cursor.close()

            for project in projects:
                self.add_project(project[0], since=self.args.since, until=self.args.until)
        else:
            logger.debug('Adding new project(s) to database...')
            for project in self.args.add_project:
                self.add_project(project, since=self.args.since, until=self.args.until)

    def terminate(self):
        self.db.close()
        logger.debug('Closed MySQL connection.')

    def get_git_name(self, url):
            name = urlparse(url)
            name = os.path.basename(name.path)
            name = name[:name.index('.')]
            return name

    def add_project(self, url, name=None, since=datetime.datetime.utcfromtimestamp(0).isoformat(), until=datetime.datetime.today().isoformat(), fork_of=None):
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

        if self.args.force_epoch:
            logger.debug('FORCE_EPOCH set to True.')

        # If new project grab everything, otherwise grab utc epoch
        if new_project or self.args.force_epoch:
            since = self.args.since
            logger.debug(f'New project, grabbing all commit data since {since} until {until}.')
        else:
            # Find last time updated
            query = 'select last_updated from project where source_url=%s'
            cursor.execute(query, (url,))
            since = cursor.fetchone()[0]

            # Shift last update by 30 hours (server timeout) earlier to account for potential commits missed during last update
            dt = arrow.get(since).datetime - datetime.timedelta(hours=30)
            since = dt.strftime('%Y-%m-%d %H:%M:%S')

            logger.debug(f'Existing project, grabbing all commit data since {since} until {until}.')

        cursor.close()

        self.process_project(url, since=since, until=until)

        if exists:
            logger.debug(f'Project from {url} updated.')
        else:
            logger.debug(f'New project from {url} inserted.')

    def process_project(self, url, since, until):
        name = self.get_git_name(url)

        # Cloned repo
        logger.debug(f'Cloning repository "{name}". This may take a while...')
        project = GitCommand('.')
        project.cloneRepo(url)
        branches = not self.args.no_branches
        data = project.getRepoCommitData('.', since=since, until=until, includebranches=branches)
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

                dt = arrow.get(date).datetime.strftime('%Y-%m-%d %H:%M:%S')
                #dt = datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S%z').strftime('%Y-%m-%d %H:%M:%S')
                message = commit['message'].strip()
                branches = commit['branches']
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
        if not self.args.keep_repos:
            os.chdir('..')
            shutil.rmtree(f'./{name}/')
            logger.debug(f'Removed repository {name}')

        cursor.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # Connection Arguments
    parser.add_argument('--host', help='host for mysql connection', type=str, default='localhost')
    parser.add_argument('--username', help='username for mysql connection', type=str, required=True)
    parser.add_argument('--password', help='password for mysql connection', type=str, required=True)
    parser.add_argument('--port', help='port for mysql connection', type=int, default=3331)
    parser.add_argument('--database', help='database for mysql connection', type=str, default='ideas_db')

    # Update Arguments
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--update', help='update existing projects on database', action='store_true')
    group.add_argument('--add_project', help='add git url(s) to database', type=str, nargs='+')

    # Misc Arguments
    parser.add_argument('--force_epoch', help='force update from utc epoch', action='store_true')
    parser.add_argument('--keep_repos', help='keep repos on disk after update', action='store_true')
    parser.add_argument('--no_branches', help='does not fetch branch names for each commit', action='store_true')
    parser.add_argument('--since', help='fetch commits from this date (ISO8601)', type=str, default=datetime.datetime.utcfromtimestamp(0).isoformat())
    parser.add_argument('--until', help='fetch commits to this date (ISO8601)', type=str, default=datetime.datetime.today().isoformat())

    args = parser.parse_args()
    DatabaseInterface(args)
