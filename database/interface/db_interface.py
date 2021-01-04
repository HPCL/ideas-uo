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

    def add_project(self, url, name=None, since=datetime.datetime.now().isoformat()):
        '''
            url: url to git file
            name: descriptive name of project, defaults to .git file name
        '''
        if not name:
            name = self.get_git_name(url)

        cursor = self.db.cursor()

        # TODO: Check similar urls (i.e. https://example.org, http://example.org, example.org/)
        cursor.execute(f'select count(*) from project where source_url="{url}"')
        exists = cursor.fetchone()[0] == 1

        if exists:
            logger.debug('Found existing git project.')
            new_project = False

            # Update existing project
            cursor.execute(f'select id from project where source_url="{url}"')
            project_id = cursor.fetchone()[0]
            cursor.execute(f'update project set last_updated=utc_timestamp() where id={project_id}')
        else:
            logger.debug('Unknown git project.')
            new_project = True

            # Insert new project
            cursor.execute(f'insert into project (name, source_url, last_updated) values ("{name}", "{url}", utc_timestamp())')

        self.db.commit()

        # If new project grab everything, otherwise grab utc epoch
        if new_project:
            since = datetime.datetime.utcfromtimestamp(0).isoformat()
            logger.debug(f'New project, grabbing all commit data since {since}.')
        else:
            # Find last time updated
            cursor.execute(f'select last_updated from project where source_url="{url}"')
            since = cursor.fetchone()[0]
            logger.debug(f'Existing project, grabbing all commit data since {since}.')

        cursor.close()

        self.process_project(url, since=since)

        if exists:
            logger.debug(f'Project from "{url}" updated.')
        else:
            logger.debug(f'New project from "{url}" inserted.')

    def process_project(self, url, since):
        name = self.get_git_name(url)

        # Cloned repo
        project = GitCommand('.')
        project.cloneRepo(url)
        data = project.getRepoCommitData('.', since=since)
        logger.debug(f'Cloned repository "{name}".')

        cursor = self.db.cursor()

        # Get project id
        cursor.execute(f'select id from project where source_url="{url}"')
        project_id = cursor.fetchone()[0]

        # Insert authors
        for author in data.keys():
            entry = author.decode('utf-8')
            username = entry[:entry.index('<') - 1]
            email = entry[entry.index('<') + 1:-1]
            cursor.execute(f'select count(*) from author where username="{username}" and email="{email}"')
            exists = cursor.fetchone()[0] == 1
            if not exists:
                cursor.execute(f'insert into author (username, email) values ("{username}", "{email}")')
                self.db.commit()

                logger.debug(f'Inserted new author "{username}".')

            # Get author id
            cursor.execute(f'select id from author where username="{username}" and email="{email}"')
            author_id = cursor.fetchone()[0]

            # Update bridge table
            cursor.execute(f'select count(*) from project_has_author where author_id={author_id} and project_id={project_id}')
            exists = cursor.fetchone()[0] == 1
            if not exists:
                cursor.execute(f'insert into project_has_author (author_id, project_id) values ({author_id}, {project_id})')
                self.db.commit()

                logger.debug(f'Inserted author {author_id} works on project {project_id}')

            # Insert commits
            for commit in data[author]['commits']:
                hash = commit['id'].decode('utf-8')
                cursor.execute(f'select count(*) from commit where hash="{hash}"')
                exists = cursor.fetchone()[0] == 1
                # Skip existing commits
                if exists:
                    logger.debug(f'Commit "{hash}" already exists.')
                    continue

                date = commit['date'].decode('utf-8')
                dt = datetime.datetime.strptime(date, '%a %b %d %H:%M:%S %Y %z').strftime('%Y-%m-%d %H:%M:%S')
                message = commit['message']
                #cursor.execute(f'insert into commit (hash, datetime, author_id, project_id, message) values ("{hash}", "{dt}", {author_id}, {project_id}, "{message}")')
                #self.db.commit()

                logger.debug(f'Inserted new commit "{hash}".')

                # Get commit id
                #cursor.execute(f'select id from commit where hash="{hash}"')
                #commit_id = cursor.fetchone()[0]

                # Insert diffs
                for diff in commit['diffs']:
                    continue # TODO: insert diffs once GitCommand fixed
                    body = '\n'.join(diff['diff'])
                    filename = diff['filename']
                    filename = filename[filename.index('/'):filename.index(' ')]
                    print(f'\t\t{filename}')
                    c = body.count('\n')
                    print(f'\t\t{c}')
                    if filename == '/code/__init.py':
                        print(body)
                    print('-' * 50)
                print('=' * 50)

        # Remove cloned repo
        os.chdir('..')
        shutil.rmtree(f'./{name}/')
        logger.debug(f'Removed repository "{name}".')
        cursor.close()

if __name__ == '__main__':
    interface = DatabaseInterface()
    url = 'https://github.com/HPCL/ideas-uo.git'
    interface.add_project(url)
