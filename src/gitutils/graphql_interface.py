import enum
import logging
import json
import requests

from src.gitutils.graphql_queries import *

GITHUB_TOKEN = 'secret'
GITLAB_TOKEN = 'secret'

class Source(enum.Enum):
    GITHUB = {'url': 'https://api.github.com/graphql',
              'headers': {'Authorization': f'bearer {GITHUB_TOKEN}'}}

    GITLAB = {'url': 'https://gitlab.com/api/graphql',
              'headers': {'Authorization': f'Bearer {GITLAB_TOKEN}'}}

def fetch_issues(owner, repo, source):
    if not isinstance(source, Source):
        raise Exception(f'Unknown source: {source}')

    payload = source.value
    issue = GITHUB_ISSUE if source == Source.GITHUB else GITLAB_ISSUE
    stage = 'repository' if source == Source.GITHUB else 'project'

    import time
    cursor = None
    start = time.time()
    while True:
        payload['json'] = {'query': issue % (owner, repo),
                       'variables': {'cursor': cursor}}
        r = requests.post(**payload)
        j = r.json()
        entry = j['data'][stage]['issues']
        pagination = entry['pageInfo']
        if source == Source.GITHUB:
            print(entry['totalCount'])
        else:
            print(entry['count'])
        print(entry['nodes'].__len__())
        for node in entry['nodes']:
            print(node)
            break
        break
        cursor = pagination['endCursor']
        if not pagination['hasNextPage']:
            break

    end = time.time()
    print(f'Done in {end - start:.2f}s.')

fetch_issues('petsc', 'petsc', Source.GITLAB)
fetch_issues('pytorch', 'pytorch', Source.GITHUB)
