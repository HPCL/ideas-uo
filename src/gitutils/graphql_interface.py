import configparser
import enum
import logging
import json
import requests

from src.gitutils.graphql_queries import *

config = configparser.ConfigParser()
config.read('credentials.ini')
GITHUB_TOKEN = config.get('github', 'token')
GITLAB_TOKEN = config.get('gitlab', 'token')

class Source(enum.Enum):
    GITHUB = {'url': 'https://api.github.com/graphql',
              'headers': {'Authorization': f'bearer {GITHUB_TOKEN}'}}

    GITLAB = {'url': 'https://gitlab.com/api/graphql',
              'headers': {'Authorization': f'Bearer {GITLAB_TOKEN}'}}

def fetch_issues(owner, repo, source):
    if not isinstance(source, Source):
        raise Exception(f'Unknown source: {source}')

    payload = source.value
    query = GITHUB_ISSUE if source == Source.GITHUB else GITLAB_ISSUE
    stage = 'repository' if source == Source.GITHUB else 'project'

    import time
    cursor = None
    print(f'Fetching issues from {source.name}...')
    issues = []
    start = time.time()
    while True:
        payload['json'] = {'query': query % (owner, repo),
                       'variables': {'cursor': cursor}}
        r = requests.post(**payload)
        j = r.json()
        try:
            entry = j['data'][stage]['issues']
            #print(j)
        except:
            print(j)
            print('Connection error with GraphQL')
            break
        pagination = entry['pageInfo']

        for node in entry['nodes']:
            issue = {}
            issue['title'] = node['title']
            issue['description'] = node['description'] if source == Source.GITLAB else node['body']
            issue['updatedAt'] = node['updatedAt']
            issue['closedAt'] = node['closedAt']
            issue['locked'] = node['discussionLocked'] if source == Source.GITLAB else node['locked']
            issue['url'] = node['webUrl'] if source == Source.GITLAB else node['url']
            issue['number'] = node['iid'] if source == Source.GITLAB else node['number']

            try:
                username = node['author']['username'] if source == Source.GITLAB else node['author']['login']
            except:
                username = None

            try:
                url = node['author']['webUrl'] if source == Source.GITLAB else node['author']['url']
            except:
                url = None

            issue['author'] = {
                'username': username,
                'url': url
            }

            def collect_assignee(node):
                return {
                    'name': node['name'],
                    'username': node['username'] if source == Source.GITLAB else node['login'],
                    'email': node['publicEmail'] if source == Source.GITLAB else node['email'],
                    'url': node['webUrl'] if source == Source.GITLAB else node['url']
                }

            issue['assignees'] = [collect_assignee(assignee) for assignee in node['assignees']['nodes']]
            issue['milestone'] = None if not node['milestone'] else {
                'state': node['milestone']['state'],
                'description': node['milestone']['description'],
                'title': node['milestone']['title'],
                'dueOn': node['milestone']['dueDate'] if source == Source.GITLAB else node['milestone']['dueOn'],
                'createdAt': node['milestone']['createdAt'],
                'updatedAt': node['milestone']['updatedAt']
            }

            def collect_label(node):
                return {
                    'name': node['title'] if source == Source.GITLAB else node['name']
                }

            issue['labels'] = [collect_label(label) for label in node['labels']['nodes']]

            def collect_comment(node):
                try:
                    username = node['author']['username'] if source == Source.GITLAB else node['author']['login']
                except:
                    username = None

                try:
                    url = node['author']['webUrl'] if source == Source.GITLAB else node['author']['url']
                except:
                    url = None

                return {
                    'author': {
                        'username': username,
                        'url': url
                    },
                    'createdAt': node['createdAt'],
                    'updatedAt': node['updatedAt'],
                    'url': node['url'],
                    'id': node['id'],
                    'body': node['body']
                }

            centry = 'notes' if source == Source.GITLAB else 'comments'
            issue['comments'] = [collect_comment(comment) for comment in node[centry]['nodes'] if comment]

            issues.append(issue)
        print('.', end='')

        cursor = pagination['endCursor']
        if not pagination['hasNextPage']:
            break

    print()
    end = time.time()
    print(f'Done in {end - start:.2f}s.')
    print(f'Got {len(issues)} issues.')
    return issues

fetch_issues('petsc', 'petsc', Source.GITLAB)
fetch_issues('google', 'gvisor', Source.GITHUB)
