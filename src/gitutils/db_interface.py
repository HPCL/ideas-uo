#!/usr/bin/env python3

import argparse
import atexit
import configparser
import datetime
import logging
import os
import shutil
from urllib.parse import urlparse

import arrow
import MySQLdb

from src.gitutils.gitcommand import GitCommand
from src.gitutils.graphql_interface import fetch_prs, fetch_issues, Source
from src.gitutils.github_api import GitHubAPIClient

# Setup Logger
logger = logging.getLogger('db_interface')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(level=logging.DEBUG)
formatter = logging.Formatter(fmt="[%(levelname)s]: %(asctime)s - %(message)s")
ch.setFormatter(fmt=formatter)
logger.addHandler(hdlr=ch)

# Read API credentials
config = configparser.ConfigParser()
config.read('credentials.ini')
GITHUB_LOGIN = config.get('github', 'login')
GITHUB_TOKEN = config.get('github', 'token')

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

        if self.args.add_project:
            logger.debug('Adding new project(s) to database...')
            project = self.args.add_project
            self.add_project(project, since=self.args.since, until=self.args.until, fork_of=self.args.fork_of, child_of=self.args.child_of, tags=self.args.tags)

        elif self.args.add_issues:
            logger.debug('Adding GitHub/GitLab issues & comments to database...')
            project = self.args.add_issues
            self.add_issues(project, since=self.args.since, until=self.args.until)

        elif self.args.add_prs:
            logger.debug('Adding GitHub/GitLab prs & comments to database...')
            project = self.args.add_prs
            self.add_prs(project, since=self.args.since, until=self.args.until)

        elif self.args.add_events:
            logger.debug('Adding GitHub events to database...')
            project = self.args.add_events
            self.add_events(project)

        else:
            raise Exception('Unknown argument mode.')

    def terminate(self):
        self.db.close()
        logger.debug('Closed MySQL connection.')

    def get_git_name(self, url):
        if url.find('.')>0:
            name = urlparse(url)
            name = os.path.basename(name.path)
            name = name[:name.index('.')]
            name
        else:
            # Local path
            name = os.path.split(url)[-1]
        return name

    def add_prs(self, url, since, until):

        parse_url = urlparse(url)
        owner, repo = parse_url.path[1:-4].split('/')
        root = parse_url.netloc[:-4]

        cursor = self.db.cursor()

        query = 'select id from project where source_url=%s'
        cursor.execute(query, (url,))
        project_id = cursor.fetchone()[0]

        if 'ECP-Astro' in url:
            project_id = 26

        if root.lower() == 'github':
            logger.debug('Source is GitHub.')
            source = Source.GITHUB
        elif root.lower() == 'gitlab':
            logger.debug('Source is GitLab.')
            source = Source.GITLAB
        else:
            logger.critical(f'Unknown source: {root}')
            raise Exception(f'Unknown source: {root}')

        # This may take a while
        logger.debug('Fetching prs. This may take a while...')

        prs = fetch_prs(owner, repo, source)
        logger.debug(f'Got {len(prs)} prs.')

        for pr in prs:
            username = pr['author']['username']
            email = pr['author']['email']
            name = pr['author']['name']
            aurl = pr['author']['url']

            query = 'select count(*) from author where username=%s and url=%s'
            cursor.execute(query, (username, aurl,))
            exists = cursor.fetchone()[0] != 0

            if not exists:
                query = 'insert into author (username, email, name, url) values (%s, %s, %s, %s)'
                cursor.execute(query, (username, email, name, aurl,))
                self.db.commit()

                logger.debug(f'Inserted new author {username}.')

            # Get author id
            query = 'select id from author where username=%s and url=%s'
            cursor.execute(query, (username, aurl,))
            author_id = cursor.fetchone()[0]

            title = pr['title']
            description = pr['description']
            updated_at = pr['updatedAt']
            locked = pr['locked']
            purl = pr['url']
            number = pr['number']
            state = pr['state']
            labels = pr['labels']
            assignees = pr['assignees']
            milestone = pr['milestone']
            comments = pr['comments']
            merged_at = pr['mergedAt']
            created_at = pr['createdAt']
            head_sha = pr['head_sha']
            commits = pr['commits']
            linked_issues = pr['linked_issues']

            updated_at = arrow.get(updated_at).datetime.strftime('%Y-%m-%d %H:%M:%S')
            merged_at = arrow.get(merged_at).datetime.strftime('%Y-%m-%d %H:%M:%S')
            created_at = arrow.get(created_at).datetime.strftime('%Y-%m-%d %H:%M:%S')

            query = 'select count(*) from pr where url=%s'
            cursor.execute(query, (purl,))
            exists = cursor.fetchone()[0] != 0

            # Insert pr

            if exists:
                logger.debug('Found existing pr.')
                query = 'update pr set title = %s, description = %s, updated_at = %s, merged_at = %s, locked = %s, state = %s where url = %s and project_id = %s and head_sha = %s and created_at = %s'
                cursor.execute(query, (title, description, updated_at, merged_at, locked, state, purl, project_id, head_sha, created_at))
            else:
                logger.debug('Inserting new pr.')
                query = 'insert into pr (title, description, updated_at, merged_at, locked, number, state, url, author_id, project_id, head_sha, created_at) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'
                cursor.execute(query, (title, description, updated_at, merged_at, locked, number, state, purl, author_id, project_id, head_sha, created_at))

            self.db.commit()

            # Get pr id
            query = 'select id from pr where url = %s and author_id = %s and number = %s'
            cursor.execute(query, (purl, author_id, number))
            pr_id = cursor.fetchone()[0]

            # Insert linked issues
            if pr['linked_issues']:
                for ref_link in linked_issues:
                    issue_url = ref_link['url']
                    query = 'select count(*) from issue_tag where url = %s'
                    cursor.execute(query, (issue_url,))
                    exists = cursor.fetchone()[0] != 0

                    if not exists:
                        query = 'insert into issue_tag (url) values (%s)'
                        cursor.execute(query, (issue_url,))
                        self.db.commit()

                    query = 'select id from issue_tag where url = %s'
                    cursor.execute(query, (issue_url,))
                    issue_id = cursor.fetchone()[0]

                    query = 'select count(*) from pr_has_issue where pr_id = %s and issue_id = %s'
                    cursor.execute(query, (pr_id, issue_id))
                    exists = cursor.fetchone()[0] != 0
                    if not exists:
                        logger.debug(f'Inserting issue tag {issue_id} for pr {pr_id}')
                        query = 'insert into pr_has_issue (pr_id, issue_id) values (%s, %s)'
                        cursor.execute(query, (pr_id, issue_id))
                        self.db.commit()

            # Insert milestone
            if pr['milestone']:
                title = pr['milestone']['title']
                description = pr['milestone']['description']
                updated_at = pr['milestone']['updatedAt']
                created_at = pr['milestone']['createdAt']
                state = pr['milestone']['state']
                due_on = pr['milestone']['dueOn']

                updated_at = arrow.get(updated_at).datetime.strftime('%Y-%m-%d %H:%M:%S')
                created_at = arrow.get(created_at).datetime.strftime('%Y-%m-%d %H:%M:%S')
                due_on = arrow.get(due_on).datetime.strftime('%Y-%m-%d %H:%M:%S')

                query = 'select count(*) from milestone where pr_id = %s'
                cursor.execute(query, (pr_id,))
                exists = cursor.fetchone()[0] != 0

                if exists:
                    logger.debug('Found existing milestone.')
                    query = 'update milestone set state = %s, description = %s, title = %s, due_on = %s, created_at = %s, updated_at = %s where pr_id = %s'
                    cursor.execute(query, (state, description, title, due_on, created_at, updated_at, pr_id,))
                else:
                    logger.debug('Inserting new milestone.')
                    query = 'insert into milestone (state, description, title, due_on, created_at, updated_at, pr_id) values (%s, %s, %s, %s, %s, %s, %s)'
                    cursor.execute(query, (state, description, title, due_on, created_at, updated_at, pr_id,))

                self.db.commit()

            # Insert labels
            for label in labels:
                query = 'select count(*) from label where name = %s'
                cursor.execute(query, (label['name'],))
                exists = cursor.fetchone()[0] != 0

                if not exists:
                    logger.debug('Inserting new label.')
                    query = 'insert into label (name) values (%s)'
                    cursor.execute(query, (label['name'],))
                    self.db.commit()

                query = 'select id from label where name = %s'
                cursor.execute(query, (label['name'],))
                label_id = cursor.fetchone()[0]

                query = 'select count(*) from pr_has_label where pr_id = %s and label_id = %s'
                cursor.execute(query, (pr_id, label_id,))
                exists = cursor.fetchone()[0] != 0

                if not exists:
                    query = 'insert into pr_has_label (pr_id, label_id) values (%s, %s)'
                    cursor.execute(query, (pr_id, label_id,))
                    self.db.commit()

            # Insert assignees
            for assignee in assignees:
                query = 'select count(*) from author where username = %s and url = %s'
                cursor.execute(query, (assignee['username'], assignee['url'],))
                exists = cursor.fetchone()[0] != 0

                if not exists:
                    query = 'insert into author (username, email, name, url) values (%s, %s, %s, %s)'
                    cursor.execute(query, (assignee['username'], assignee['email'], assignee['name'], assignee['url'],))
                    self.db.commit()

                query = 'select id from author where username = %s and url = %s'
                cursor.execute(query, (assignee['username'], assignee['url'],))
                assignee_id = cursor.fetchone()[0]

                query = 'select count(*) from pr_has_assignee where pr_id = %s and assignee_id = %s'
                cursor.execute(query, (pr_id, assignee_id,))
                exists = cursor.fetchone()[0] != 0

                if not exists:
                    query = 'insert into pr_has_assignee (pr_id, assignee_id) values (%s, %s)'
                    cursor.execute(query, (pr_id, assignee_id,))
                    self.db.commit()

            # Insert commits
            for commit in commits:
                sha = commit['sha']
                query = 'select count(*) from commit_tag where sha = %s'
                cursor.execute(query, (sha,))
                exists = cursor.fetchone()[0] != 0

                if not exists:
                    query = 'insert into commit_tag (sha) values (%s)'
                    cursor.execute(query, (sha,))
                    self.db.commit()

                query = 'select id from commit_tag where sha = %s'
                cursor.execute(query, (sha,))
                commit_id = cursor.fetchone()[0]

                query = 'select count(*) from pr_has_commit where pr_id = %s and commit_id = %s'
                cursor.execute(query, (pr_id, commit_id))
                exists = cursor.fetchone()[0] != 0
                if not exists:
                    logger.debug(f'Inserting commit tag {commit_id} for pr {pr_id}')
                    query = 'insert into pr_has_commit (pr_id, commit_id) values (%s, %s)'
                    cursor.execute(query, (pr_id, commit_id))
                    self.db.commit()


            # Insert comments
            for comment in comments:
                query = 'select count(*) from author where username = %s and url = %s'
                cursor.execute(query, (comment['author']['username'], comment['author']['url'],))
                exists = cursor.fetchone()[0] != 0

                if not exists:
                    query = 'insert into author (username, url) values (%s, %s)'
                    cursor.execute(query, (comment['author']['username'], comment['author']['url'],))
                    self.db.commit()

                query = 'select id from author where username = %s and url = %s'
                cursor.execute(query, (comment['author']['username'], comment['author']['url'],))
                author_id = cursor.fetchone()[0]

                created_at = comment['createdAt']
                updated_at = comment['updatedAt']

                updated_at = arrow.get(updated_at).datetime.strftime('%Y-%m-%d %H:%M:%S')
                created_at = arrow.get(created_at).datetime.strftime('%Y-%m-%d %H:%M:%S')

                query = 'select count(*) from comment where pr_id = %s and author_id = %s and created_at = %s and updated_at = %s'
                cursor.execute(query, (pr_id, author_id, created_at, updated_at))
                exists = cursor.fetchone()[0] != 0

                if not exists:
                    logger.debug(f'Inserting new comment for pr {pr_id} from author {author_id}')
                    query = 'insert into comment (pr_id, author_id, created_at, updated_at, body) values (%s, %s, %s, %s, %s)'
                    cursor.execute(query, (pr_id, author_id, created_at, updated_at, comment['body']))
                    self.db.commit()

        cursor.close()

    def add_issues(self, url, since, until):

        parse_url = urlparse(url)
        owner, repo = parse_url.path[1:-4].split('/')
        root = parse_url.netloc[:-4]

        cursor = self.db.cursor()

        query = 'select id from project where source_url=%s'
        cursor.execute(query, (url,))
        project_id = cursor.fetchone()[0]

        if 'ECP-Astro' in url:
            project_id = 26

        if root.lower() == 'github':
            logger.debug('Source is GitHub.')
            source = Source.GITHUB
        elif root.lower() == 'gitlab':
            logger.debug('Source is GitLab.')
            source = Source.GITLAB
        else:
            logger.critical(f'Unknown source: {root}')
            raise Exception(f'Unknown source: {root}')

        # This may take a while
        logger.debug('Fetching issues. This may take a while...')

        issues = fetch_issues(owner, repo, source)
        logger.debug(f'Got {len(issues)} issues.')

        for issue in issues:
            username = issue['author']['username']
            email = issue['author']['email']
            name = issue['author']['name']
            aurl = issue['author']['url']

            query = 'select count(*) from author where username=%s and url=%s'
            cursor.execute(query, (username, aurl,))
            exists = cursor.fetchone()[0] != 0

            if not exists:
                query = 'insert into author (username, email, name, url) values (%s, %s, %s, %s)'
                cursor.execute(query, (username, email, name, aurl,))
                self.db.commit()

                logger.debug(f'Inserted new author {username}.')

            # Get author id
            query = 'select id from author where username=%s and url=%s'
            cursor.execute(query, (username, aurl,))
            author_id = cursor.fetchone()[0]

            title = issue['title']
            description = issue['description']
            updated_at = issue['updatedAt']
            locked = issue['locked']
            iurl = issue['url']
            number = issue['number']
            closed_at = issue['closedAt']
            created_at = issue['createdAt']
            state = issue['state']
            labels = issue['labels']
            assignees = issue['assignees']
            milestone = issue['milestone']
            comments = issue['comments']

            updated_at = arrow.get(updated_at).datetime.strftime('%Y-%m-%d %H:%M:%S')
            closed_at = arrow.get(closed_at).datetime.strftime('%Y-%m-%d %H:%M:%S')
            created_at = arrow.get(created_at).datetime.strftime('%Y-%m-%d %H:%M:%S')

            query = 'select count(*) from issue where url=%s'
            cursor.execute(query, (iurl,))
            exists = cursor.fetchone()[0] != 0
            # Insert issue

            if exists:
                logger.debug('Found existing issue.')
                query = 'update issue set title = %s, description = %s, updated_at = %s, closed_at = %s, locked = %s, state = %s where url = %s and project_id = %s and created_at = %s'
                cursor.execute(query, (title, description, updated_at, closed_at, locked, state, iurl, project_id, created_at))
            else:
                logger.debug('Inserting new issue.')
                query = 'insert into issue (title, description, updated_at, closed_at, locked, number, state, url, author_id, project_id, created_at) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'
                cursor.execute(query, (title, description, updated_at, closed_at, locked, number, state, iurl, author_id, project_id, created_at))

            self.db.commit()

            # Get issue id
            query = 'select id from issue where url = %s and author_id = %s and number = %s'
            cursor.execute(query, (iurl, author_id, number))
            issue_id = cursor.fetchone()[0]

            # Insert milestone
            if issue['milestone']:
                title = issue['milestone']['title']
                description = issue['milestone']['description']
                updated_at = issue['milestone']['updatedAt']
                created_at = issue['milestone']['createdAt']
                state = issue['milestone']['state']
                due_on = issue['milestone']['dueOn']

                updated_at = arrow.get(updated_at).datetime.strftime('%Y-%m-%d %H:%M:%S')
                created_at = arrow.get(created_at).datetime.strftime('%Y-%m-%d %H:%M:%S')
                due_on = arrow.get(due_on).datetime.strftime('%Y-%m-%d %H:%M:%S')

                query = 'select count(*) from milestone where issue_id = %s'
                cursor.execute(query, (issue_id,))
                exists = cursor.fetchone()[0] != 0

                if exists:
                    logger.debug('Found existing milestone.')
                    query = 'update milestone set state = %s, description = %s, title = %s, due_on = %s, created_at = %s, updated_at = %s where issue_id = %s'
                    cursor.execute(query, (state, description, title, due_on, created_at, updated_at, issue_id,))
                else:
                    logger.debug('Inserting new milestone.')
                    query = 'insert into milestone (state, description, title, due_on, created_at, updated_at, issue_id) values (%s, %s, %s, %s, %s, %s, %s)'
                    cursor.execute(query, (state, description, title, due_on, created_at, updated_at, issue_id,))

                self.db.commit()

            # Insert labels
            for label in labels:
                query = 'select count(*) from label where name = %s'
                cursor.execute(query, (label['name'],))
                exists = cursor.fetchone()[0] != 0

                if not exists:
                    logger.debug('Inserting new label.')
                    query = 'insert into label (name) values (%s)'
                    cursor.execute(query, (label['name'],))
                    self.db.commit()

                query = 'select id from label where name = %s'
                cursor.execute(query, (label['name'],))
                label_id = cursor.fetchone()[0]

                query = 'select count(*) from issue_has_label where issue_id = %s and label_id = %s'
                cursor.execute(query, (issue_id, label_id,))
                exists = cursor.fetchone()[0] != 0

                if not exists:
                    query = 'insert into issue_has_label (issue_id, label_id) values (%s, %s)'
                    cursor.execute(query, (issue_id, label_id,))
                    self.db.commit()

            # Insert assignees
            for assignee in assignees:
                query = 'select count(*) from author where username = %s and url = %s'
                cursor.execute(query, (assignee['username'], assignee['url'],))
                exists = cursor.fetchone()[0] != 0

                if not exists:
                    query = 'insert into author (username, email, name, url) values (%s, %s, %s, %s)'
                    cursor.execute(query, (assignee['username'], assignee['email'], assignee['name'], assignee['url'],))
                    self.db.commit()

                query = 'select id from author where username = %s and url = %s'
                cursor.execute(query, (assignee['username'], assignee['url'],))
                assignee_id = cursor.fetchone()[0]

                query = 'select count(*) from issue_has_assignee where issue_id = %s and assignee_id = %s'
                cursor.execute(query, (issue_id, assignee_id,))
                exists = cursor.fetchone()[0] != 0

                if not exists:
                    query = 'insert into issue_has_assignee (issue_id, assignee_id) values (%s, %s)'
                    cursor.execute(query, (issue_id, assignee_id,))
                    self.db.commit()

            # Insert comments
            for comment in comments:
                query = 'select count(*) from author where username = %s and url = %s'
                cursor.execute(query, (comment['author']['username'], comment['author']['url'],))
                exists = cursor.fetchone()[0] != 0

                if not exists:
                    query = 'insert into author (username, url) values (%s, %s)'
                    cursor.execute(query, (comment['author']['username'], comment['author']['url'],))
                    self.db.commit()

                query = 'select id from author where username = %s and url = %s'
                cursor.execute(query, (comment['author']['username'], comment['author']['url'],))
                author_id = cursor.fetchone()[0]

                created_at = comment['createdAt']
                updated_at = comment['updatedAt']

                updated_at = arrow.get(updated_at).datetime.strftime('%Y-%m-%d %H:%M:%S')
                created_at = arrow.get(created_at).datetime.strftime('%Y-%m-%d %H:%M:%S')

                query = 'select count(*) from comment where issue_id = %s and author_id = %s and created_at = %s and updated_at = %s'
                cursor.execute(query, (issue_id, author_id, created_at, updated_at))
                exists = cursor.fetchone()[0] != 0

                if not exists:
                    logger.debug(f'Inserting new comment for issue {issue_id} from author {author_id}')
                    query = 'insert into comment (issue_id, author_id, created_at, updated_at, body) values (%s, %s, %s, %s, %s)'
                    cursor.execute(query, (issue_id, author_id, created_at, updated_at, comment['body']))
                    self.db.commit()

        cursor.close()

    def add_project(self, url, name=None, since=None, until=datetime.datetime.today().isoformat(), fork_of=None, child_of=None, tags=None):
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
        exists = cursor.fetchone()[0] != 0

        if exists:
            logger.debug('Found existing git project.')
            new_project = False

            # Update existing project
            query = 'select id from project where source_url=%s'
            cursor.execute(query, (url,))
            project_id = cursor.fetchone()[0]
        else:
            logger.debug('Unknown git project.')
            new_project = True

            # If fork, find parent project_id
            if fork_of:
                #TODO: Currently assumes parent project already exists -- throw error otherwise?
                query = 'select id from project where source_url=%s'
                cursor.execute(query, (fork_of,))
                fork_of = cursor.fetchone()[0]

            # If child, find parent project_id
            if child_of:
                #TODO: See above in fork_of if-clause
                query = 'select id from project where source_url=%s'
                cursor.execute(query, (child_if,))
                child_of = cursor.fetchone()[0]

            # Insert new project
            # TODO: update has_github and has_gitlab
            query = 'insert into project (name, source_url, last_updated, fork_of_id, child_of_id, has_github, has_gitlab, github_last_updated, gitlab_last_updated) values (%s, %s, utc_timestamp(), %s, %s, 0, 0, utc_timestamp(), utc_timestamp())'
            cursor.execute(query, (name, url, fork_of, child_of))

        self.db.commit()

        # If tags specified add them
        if tags:
            query = 'select id from project where source_url=%s'
            cursor.execute(query, (url,))
            project_id = cursor.fetchone()[0]

            # Add tags
            query = 'insert into tag (tag) values (%s)'
            cursor.executemany(query, [(tag,) for tag in tags])
            self.db.commit()

            for tag in tags:
                logger.debug(f'Inserted tag {tag}')

            # Add to bridge table
            query = 'select id from tag where tag=%s'
            tag_ids = []

            for tag in tags:
                cursor.execute(query, (tag,))
                tag_id = cursor.fetchone()[0]
                tag_ids.append(tag_id)

            query = 'insert into project_has_tag (project_id, tag_id) values (%s, %s)'
            cursor.executemany(query, [(project_id, tag_id,) for tag_id in tag_ids])
            self.db.commit()

            for tag_id in tag_ids:
                logger.debug(f'Inserted tag {tag_id} for project {project_id}')

        if self.args.force_epoch:
            logger.debug('FORCE_EPOCH set to True.')

        # If new project grab everything, otherwise grab utc epoch
        if new_project or self.args.force_epoch:
            since = self.args.since
            logger.debug(f'New project, grabbing all commit data since {since} until {until}.')
        else:
            if since == 'null':
                # Find last time updated
                query = 'select last_updated from project where source_url=%s'
                cursor.execute(query, (url,))
                since = cursor.fetchone()[0]

            # Shift last update by 30 hours (server timeout) earlier to account for potential commits missed during last update
            dt = arrow.get(since).datetime - datetime.timedelta(hours=30)
            since = dt.strftime('%Y-%m-%d %H:%M:%S')

            logger.debug(f'Existing project, grabbing all commit data since {since} until {until}.')

        cursor.close()

        # TODO: fix since (gets from Unix Epoch only right now (default arg))
        self.process_project(url, since=since, until=until)

        if exists:
            logger.debug(f'Project from {url} updated.')
        else:
            logger.debug(f'New project from {url} inserted.')

        query = 'update project set last_updated=utc_timestamp() where id=%s'
        cursor.execute(query, (project_id,))
        self.db.commit()

    def process_project(self, url, since, until):
        name = self.get_git_name(url)
        branches = not self.args.no_branches
        since = arrow.get(since).datetime.isoformat()
        logger.debug(f'Mining repository "{name}". This may take a while...')

        if url[0] == '/':
            logger.debug('Working on local repository.')
            repo_dir = os.path.join(os.getcwd(), 'repos')
            project = GitCommand(repo_dir)
            data = project.getRepoCommitData(name, since=since, until=until, includebranches=branches)
        else:
            logger.debug('Working on remote repository.')
            project = GitCommand('.')
            project.cloneRepo(url)
            data = project.getRepoCommitData('.', since=since, until=until, includebranches=branches)

        logger.debug(f'Mined repository "{name}".')
        cursor = self.db.cursor()

        # Get project id
        query = 'select id from project where source_url=%s'
        cursor.execute(query, (url,))
        project_id = cursor.fetchone()[0]

        if 'ECP-Astro' in url:
            project_id = 26

        # Insert authors
        for author in data.keys():
            entry = author.decode('utf-8')
            username = entry[:entry.index('<') - 1]
            email = entry[entry.index('<') + 1:-1]

            query = 'select count(*) from author where username=%s and email=%s'
            cursor.execute(query, (username, email,))
            exists = cursor.fetchone()[0] != 0
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
            exists = cursor.fetchone()[0] != 0
            if not exists:
                query = 'insert into project_has_author (author_id, project_id) values (%s, %s)'
                cursor.execute(query, (author_id, project_id,))
                self.db.commit()

                logger.debug(f'Inserted author {author_id} works on project {project_id}')

            # Insert commits
            for commit in data[author]['commits']:
                hash = commit['id']
                date = commit['date'].decode('utf-8')
                dt = arrow.get(date).datetime.strftime('%Y-%m-%d %H:%M:%S')
                #dt = datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S%z').strftime('%Y-%m-%d %H:%M:%S')
                message = commit['message'].strip()
                branches = commit['branches']
                query = 'select count(*) from commit where hash=%s'
                cursor.execute(query, (hash,))
                exists = cursor.fetchone()[0] != 0

                # Skip existing commits
                if exists:
                    logger.debug(f'Commit {hash} already exists.')
                    query = 'update commit set branch=%s where hash=%s'
                    cursor.execute(query, (branches, hash,))
                    continue

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

        cursor.close()


    def add_events(self, url):
        cursor = self.db.cursor()

        if url == '/shared/repos/FLASH5':
            project_id = 26
            owner, repo = 'ECP-Astro', 'FLASH5'
        else:
            parse_url = urlparse(url)
            owner, repo = parse_url.path[1:-4].split('/')
            root = parse_url.netloc[:-4]

            query = 'select id from project where source_url=%s'
            cursor.execute(query, (url,))
            project_id = cursor.fetchone()[0]

        GitHubAPIClient.set_credentials(username=GITHUB_LOGIN, token=GITHUB_TOKEN)
        GitHubAPIClient.check_credentials()

        logger.debug('Grabbing GitHub events from API...')
        data = GitHubAPIClient.fetch_events(owner=owner, repository=repo)

        for event in data:
            # Check if new event
            api_id = event['id']
            type = event['type']
            public = event['public']
            created_at = event['created_at']
            created_at = arrow.get(created_at).datetime.strftime('%Y-%m-%d %H:%M:%S')
            query = f'select count(*) from event where api_id=%s and created_at=%s and project_id=%s'
            cursor.execute(query, (api_id, created_at, project_id))
            exists = cursor.fetchone()[0] != 0
            if exists:
                logger.debug('Found existing event. Skipping...')
                continue

            # Insert Event Actor
            actor_id = event['actor']['id']
            login = event['actor']['login']
            url = event['actor']['url']
            avatar_url = event['actor']['avatar_url']
            gravatar_id = event['actor']['gravatar_id']

            query = 'select count(*) from event_actor where login=%s and url=%s and actor_id=%s'
            cursor.execute(query, (login, url, actor_id,))
            exists = cursor.fetchone()[0] != 0

            if not exists:
                logger.debug(f'Inserted new event actor {login}')
                query = 'insert into event_actor (actor_id, login, url, avatar_url, gravatar_id) values (%s, %s, %s, %s, %s)'
                cursor.execute(query, (actor_id, login, url, avatar_url, gravatar_id))
                self.db.commit()

            query = 'select id from event_actor where login=%s and url=%s and actor_id=%s'
            cursor.execute(query, (login, url, actor_id,))
            event_actor_id = cursor.fetchone()[0]

            # Insert Event Repo
            repo_id = event['repo']['id']
            name = event['repo']['name']
            url = event['repo']['url']

            query = 'select count(*) from event_repo where repo_id=%s and name=%s and url=%s'
            cursor.execute(query, (repo_id, name, url,))
            exists = cursor.fetchone()[0] != 0

            if not exists:
                logger.debug(f'Inserted new event repo {name}')
                query = 'insert into event_repo (repo_id, name, url) values (%s, %s, %s)'
                cursor.execute(query, (repo_id, name, url,))
                self.db.commit()

            query = 'select id from event_repo where repo_id=%s and name=%s and url=%s'
            cursor.execute(query, (repo_id, name, url,))
            event_repo_id = cursor.fetchone()[0]

            # Insert Event Org
            org_id = event['org']['id']
            login = event['org']['login']
            url = event['org']['url']
            avatar_url = event['org']['avatar_url']
            gravatar_id = event['org']['gravatar_id']

            query = 'select count(*) from event_org where login=%s and url=%s and org_id=%s'
            cursor.execute(query, (login, url, org_id,))
            exists = cursor.fetchone()[0] != 0

            if not exists:
                logger.debug(f'Inserted new event org {login}')
                query = 'insert into event_org (org_id, login, url, avatar_url, gravatar_id) values (%s, %s, %s, %s, %s)'
                cursor.execute(query, (org_id, login, url, avatar_url, gravatar_id))
                self.db.commit()

            query = 'select id from event_org where login=%s and url=%s and org_id=%s'
            cursor.execute(query, (login, url, org_id,))
            event_org_id = cursor.fetchone()[0]

            # Insert Event Payload

            def get_payload(attribute, key=None):
                try:
                    result = event['payload'][attribute]
                    if key:
                        result = result[key]
                except KeyError:
                    result = None
                return result

            action = get_payload('action')
            ref = get_payload('ref')
            ref_type = get_payload('ref_type')
            master_branch = get_payload('master_branch')
            description = get_payload('description')
            forkee_url = get_payload('forkee', 'html_url')
            issue_url = get_payload('issue', 'html_url')
            comment_url = get_payload('comment', 'html_url')
            member_login = get_payload('member_login')
            pr_number = get_payload('number')
            pr_url = get_payload('pull_request', 'html_url')
            pr_review_url = get_payload('review', 'html_url')
            push_id = get_payload('push_id')
            size = get_payload('size')
            distinct_size = get_payload('distinct_size')
            head_sha = get_payload('head')
            before_sha = get_payload('before')
            release_url = get_payload('release', 'html_url')
            effective_date = get_payload('effective_date')

            logger.debug('Inserted new event payload')
            query = '''insert into event_payload (action, ref, ref_type, master_branch, description, forkee_url, issue_url, comment_url, member_login, pr_number, pr_url, pr_review_url, push_id, size, distinct_size, head_sha, before_sha, release_url, effective_date) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''
            cursor.execute(query, (action, ref, ref_type, master_branch, description, forkee_url, issue_url, comment_url, member_login, pr_number, pr_url, pr_review_url, push_id, size, distinct_size, head_sha, before_sha, release_url, effective_date))
            self.db.commit()

            event_payload_id = cursor.lastrowid # may want to use this for other cases...

            # Insert Event Pages (GollumEvent (i.e. Wiki changes))
            if get_payload('pages'):
                page_ids = []
                for page in get_payload('pages'):
                    name = page['name']
                    title = page['title']
                    action = page['action']
                    sha = page['sha']
                    url = page['html_url']

                    query = 'select count(*) from event_page where name=%s and url=%s'
                    cursor.execute(query, (name, url,))
                    exists = cursor.fetchone()[0] != 0

                    logger.debug(f'Inserted new event page {name}')
                    query = 'insert into event_page (name, title, action, sha, url) values (%s, %s, %s, %s, %s)'
                    cursor.execute(query, (name, title, action, sha, url,))
                    self.db.commit()

                    query = 'select id from event_org where name=%s and url=%s'
                    cursor.execute(query, (name, url,))
                    event_page_id = cursor.fetchone()[0]
                    page_ids.append(event_page_id)

                for page_id in page_ids:
                    query = f'select count(*) from event_page where id=%s'
                    cursor.execute(query, (page_id,))
                    exists = cursor.fetchone()[0] != 0

                    if not exists:
                        logger.debug('Inserted new event has event page')
                        query = 'insert into event_has_page (payload, page) values (%s, %s)'
                        cursor.execute(query, (event_payload_id, page_id))
                        self.db.commit()

            # Insert Event
            logger.debug(f'Inserted new event {type}')
            query = 'insert into event (project_id, api_id, type, public, created_at, payload_id, repo_id, actor_id, org_id) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)'
            cursor.execute(query, (project_id, api_id, type, public, created_at, event_payload_id, event_repo_id, event_actor_id, event_org_id))
            self.db.commit()

        cursor.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # Connection Arguments
    parser.add_argument('--host', help='host for mysql connection', type=str, default='sansa.cs.uoregon.edu')
    parser.add_argument('--username', help='username for mysql connection', type=str, required=True)
    parser.add_argument('--password', help='password for mysql connection', type=str, required=True)
    parser.add_argument('--port', help='port for mysql connection', type=int, default=3331)
    parser.add_argument('--database', help='database for mysql connection', type=str, default='ideas_db')

    # Update Arguments
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--add_project', help='add git url to database', type=str)
    # TODO: update graphql queries to use --since and --until
    group.add_argument('--add_issues', help='add GitHub/Gitlab issues', type=str)
    group.add_argument('--add_prs', help='add GitHub/Gitlab pull requests', type=str)
    group.add_argument('--add_events', help='add GitHub events', type=str)

    # Misc Arguments
    parser.add_argument('--force_epoch', help='force update from utc epoch', action='store_true')
    parser.add_argument('--no_branches', help='does not fetch branch names for each commit', action='store_true')
    parser.add_argument('--since', help='fetch commits from this date (ISO8601)', type=str, default='null')
    parser.add_argument('--until', help='fetch commits to this date (ISO8601)', type=str, default=datetime.datetime.today().isoformat())
    parser.add_argument('--tags', help='tags to add to project', nargs='+', type=str)
    parser.add_argument('--fork_of', help='fork of another project', type=str)
    parser.add_argument('--child_of', help='child of another project', type=str)

    args = parser.parse_args()
    DatabaseInterface(args)
