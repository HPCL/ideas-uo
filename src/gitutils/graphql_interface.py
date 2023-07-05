import configparser
import enum
import logging
import requests
import time

from .graphql_queries import *

logger = logging.getLogger('graphql_interface')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(level=logging.DEBUG)
formatter = logging.Formatter(fmt='[%(levelname)s]: %(asctime)s - %(message)s')
ch.setFormatter(fmt=formatter)
logger.addHandler(hdlr=ch)

config = configparser.ConfigParser()
config.read('credentials.ini')
GITHUB_TOKEN = config.get('github', 'token')
GITLAB_TOKEN = config.get('gitlab', 'token')

class Source(enum.Enum):
    GITHUB = {'url': 'https://api.github.com/graphql',
              'headers': {'Authorization': f'bearer {GITHUB_TOKEN}'}}

    GITLAB = {'url': 'https://gitlab.com/api/graphql',
              'headers': {'Authorization': f'Bearer {GITLAB_TOKEN}'}}

def collect_assignee(node, source):
    return {
        'name': node['name'],
        'username': node['username'] if source == Source.GITLAB else node['login'],
        'email': node['publicEmail'] if source == Source.GITLAB else node['email'],
        'url': node['webUrl'] if source == Source.GITLAB else node['url']}

def collect_label(node, source):
    return {
        'name': node['title'] if source == Source.GITLAB else node['name']}


def collect_comment(node, source):
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
            'url': url,
            'name': None,
            'email': None},

        'createdAt': node['createdAt'],
        'updatedAt': node['updatedAt'],
        'url': node['url'],
        'id': node['id'],
        'body': node['body']}

def collect_commit(node, source):
    return {'sha': node['sha'] if source == Source.GITLAB else node['commit']['oid']}

def fetch_prs(owner, repo, source):
    if not isinstance(source, Source):
        raise Exception(f'{repo}: Unknown source: {source}')

    payload = source.value
    query = GITHUB_PULLREQUEST if source == Source.GITHUB else GITLAB_PULLREQUEST
    stage = 'repository' if source == Source.GITHUB else 'project'

    cursor = None
    logger.info(f'{repo}: Fetching pull requests from {source.name}...')
    prs = []
    start = time.time()
    attempt = 0

    while True:
        payload['json'] = {'query': query % (owner, repo),
                       'variables': {'cursor': cursor}}
        j = {}
        while not 'data' in j.keys():
            logger.info(f'{repo}: Fetching data with graphql: %s' % str(payload['json']))
            r = requests.post(**payload)
            j = r.json()

            # When the API rate limit is exceeded, j is a dictionary that looks like this:
            # {'errors': [{'type': 'RATE_LIMITED', 'message': 'API rate limit exceeded for user ID 3604514.'}]}
            if 'errors' in j.keys():
                if j['errors'].get('type') == 'RATE_LIMITED':
                    logger.warn(f'{repo}: GraphQL API rate limit exceeded (5000 points per hour), going to sleep for an hour')
                    time.sleep(3600)    


        try:
            if attempt:
                logger.warning(f'{repo}: Attempt {attempt}...')
            entry = j['data'][stage]['pullRequests'] if source == Source.GITHUB else j['data'][stage]['mergeRequests']
            if not entry: # sometimes returns None
                raise Exception
            attempt = 0 # clear attempts if successful
        except Exception as err:
            attempt += 1
            logger.critical(f'{repo}: Connection error with GraphQL: {err}. Retrying...')
            continue

        pagination = entry['pageInfo']


        for node in entry['nodes']:
            pr = {}
            pr['title'] = node['title']
            pr['description'] = node['description'] if source == Source.GITLAB else node['body']
            pr['updatedAt'] = node['updatedAt']
            pr['locked'] = node['discussionLocked'] if source == Source.GITLAB else node['locked']
            pr['url'] = node['webUrl'] if source == Source.GITLAB else node['url']
            pr['number'] = node['iid'] if source == Source.GITLAB else node['number']
            pr['state'] = node['state']

            try:
                # TODO: Only for GitHub
                pr['linked_issues'] = [url for url in node['closingIssuesReferences']['nodes']]
            except:
                pr['linked_issues'] = None

            try:
                username = node['author']['username'] if source == Source.GITLAB else node['author']['login']
            except:
                username = None

            try:
                url = node['author']['webUrl'] if source == Source.GITLAB else node['author']['url']
            except:
                url = None

            pr['author'] = {
                'username': username,
                'url': url,
                'email': None,
                'name': None}

            pr['labels'] = [collect_label(label, source) for label in node['labels']['nodes']]

            pr['assignees'] = [collect_assignee(assignee, source) for assignee in node['assignees']['nodes']]
            pr['milestone'] = None if not node['milestone'] else {
                'state': node['milestone']['state'],
                'description': node['milestone']['description'],
                'title': node['milestone']['title'],
                'dueOn': node['milestone']['dueDate'] if source == Source.GITLAB else node['milestone']['dueOn'],
                'createdAt': node['milestone']['createdAt'],
                'updatedAt': node['milestone']['updatedAt']}

            #need to modify graphql_queries to make this work.  See GraphQL docs on git hub.
            #if source != Source.GITLAB:
            #    pr['review_comments'] = [collect_comment(comment, source) for comment in node['review_comments']['nodes'] if comment]

            centry = 'notes' if source == Source.GITLAB else 'comments'
            pr['comments'] = [collect_comment(comment, source) for comment in node[centry]['nodes'] if comment]
            pr['mergedAt'] = node['mergedAt']
            pr['createdAt'] = node['createdAt']
            pr['head_sha'] = node['diffHeadSha'] if source == Source.GITLAB else node['headRefOid']
            cmentry = 'commitsWithoutMergeCommits' if source == Source.GITLAB else 'commits'
            pr['commits'] = [collect_commit(commit, source) for commit in node[cmentry]['nodes']]
            prs.append(pr)

        logger.info(f'{repo}: Collected {len(entry["nodes"])} pull requests.')

        cursor = pagination['endCursor']
        if not pagination['hasNextPage']:
            break

    end = time.time()
    logger.info(f'{repo}: Done in {end - start:.2f}s.')
    logger.info(f'{repo}: Got {len(prs)} pull requests.')
    return prs


def fetch_issues(owner, repo, source):
    if not isinstance(source, Source):
        raise exception(f'{repo}: Unknown source: {source}')

    payload = source.value
    query = GITHUB_ISSUE if source == Source.GITHUB else GITLAB_ISSUE
    stage = 'repository' if source == Source.GITHUB else 'project'

    cursor = None
    logger.info(f'{repo}: Fetching issues from {source.name}...')
    issues = []
    start = time.time()
    attempt = 0

    while attempt<100:
        payload['json'] = {'query': query % (owner, repo),
                       'variables': {'cursor': cursor}}
        r = requests.post(**payload)
        j = r.json()
        try:
            if attempt:
                logger.warning(f'{repo}: Attempt {attempt}...')
            entry = j['data'][stage]['issues']
            if not entry: # sometimes returns None
                raise Exception
            attempt = 0 # clear attempts if successful
        except:
            attempt += 1
            logger.critical('Connection error with GraphQL')
            continue
        pagination = entry['pageInfo']

        for node in entry['nodes']:
            issue = {}
            issue['title'] = node['title']
            issue['description'] = node['description'] if source == Source.GITLAB else node['body']
            issue['updatedAt'] = node['updatedAt']
            issue['closedAt'] = node['closedAt']
            issue['createdAt'] = node['createdAt']
            issue['locked'] = node['discussionLocked'] if source == Source.GITLAB else node['locked']
            issue['url'] = node['webUrl'] if source == Source.GITLAB else node['url']
            issue['number'] = node['iid'] if source == Source.GITLAB else node['number']
            issue['state'] = node['state']

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
                'url': url,
                'email': None,
                'name': None
            }

            issue['labels'] = [collect_label(label, source) for label in node['labels']['nodes']]

            issue['assignees'] = [collect_assignee(assignee, source) for assignee in node['assignees']['nodes']]
            issue['milestone'] = None if not node['milestone'] else {
                'state': node['milestone']['state'],
                'description': node['milestone']['description'],
                'title': node['milestone']['title'],
                'dueOn': node['milestone']['dueDate'] if source == Source.GITLAB else node['milestone']['dueOn'],
                'createdAt': node['milestone']['createdAt'],
                'updatedAt': node['milestone']['updatedAt']
            }


            centry = 'notes' if source == Source.GITLAB else 'comments'
            issue['comments'] = [collect_comment(comment, source) for comment in node[centry]['nodes'] if comment]

            issues.append(issue)

        logger.info(f'{repo}: Collected {len(entry["nodes"])} issues.')

        cursor = pagination['endCursor']
        if not pagination['hasNextPage']:
            break

    end = time.time()
    logger.info(f'{repo}: Done in {end - start:.2f}s.')
    logger.info(f'{repo}: Got {len(issues)} issues.')
    return issues

if __name__ == '__main__':
    #fetch_prs('gitlab-org', 'gitlab-development-kit', Source.GITLAB)
    d = fetch_prs('google', 'gvisor', Source.GITHUB)
    for i in d:
        print(i['linked_issues'])
    #fetch_issues('gitlab-org', 'gitlab-development-kit', Source.GITLAB)
    #fetch_issues('google', 'gvisor', Source.GITHUB)
