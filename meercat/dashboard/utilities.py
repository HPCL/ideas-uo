import requests

from database.models import EventLog
from database.utilities import get_repo_owner
from datetime import datetime


def save_debug_event(log, json='', pull_request=None, request=None):

    if request is not None:
        uri = request.build_absolute_uri()
        view_name = request.resolver_match.view_name
        if request.user.is_anonymous:
            user = None
        else:
            user = request.user
    else:
        uri = ''
        view_name = ''
        user = None

    debug_event = EventLog(
        user=user,
        uri=uri,
        view_name=view_name,
        event_type=EventLog.EventTypeChoices.DEBUGGING,
        datetime=datetime.today(),
        log=log,
        json=json,
        pull_request=pull_request
    )
    debug_event.save()


def get_branches_with_status(project): # only works with public repos for now
    repo_owner = get_repo_owner(project)
    repo_name = project.name

    pulls_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls?state=all"
    branches_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/branches"

    pulls = requests.get(pulls_url).json()
    branches = requests.get(branches_url).json()

    branch_names = [branch['name'] for branch in branches]
    processed_branches = []
    branches_with_status = []

    # Process branches with pull request
    for pr in pulls:
        branch_name = pr['head']['ref']
        if branch_name in branch_names and branch_name not in processed_branches:
            branches_with_status.append({'branch': branch_name, 'status': pr['state']})
            processed_branches.append(branch_name)

    # Process branches without pull request
    for branch_name in branch_names:
        if branch_name not in processed_branches:
            branches_with_status.append({'branch': branch_name, 'status': 'No Pull Request'})

    return branches_with_status