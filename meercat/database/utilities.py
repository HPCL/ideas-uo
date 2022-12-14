import requests
import json
from datetime import datetime
from pathlib import Path
from database.models import EventLog
from django.conf import settings

BASE_DIR = Path(__file__).resolve().parent.parent
with open(settings.BASE_DIR / 'meercat.config.json') as meercat_config:
    config = json.load(meercat_config)

def get_repo_owner(repo):
    return repo.source_url.split('/')[-2] # owner is always second to last when spliting url by /

def comment_pullrequest(pull_request, comment):
    repo_name = pull_request.project.name
    repo_owner = get_repo_owner(pull_request.project)
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{pull_request.number}/comments"
    payload = { "body": comment }
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization" : "token " + config['MEERCAT_USER_TOKEN']
    }

    result = requests.post(url, headers=headers, data=json.dumps(payload))

    if result.status_code >= 400:
        event = EventLog(
            event_type=EventLog.EventTypeChoices.NOTIFICATION_FAIL, 
            log=result.text,
            pull_request=pull_request,
            datetime=datetime.today()
        )
    else:
        event = EventLog(
            event_type=EventLog.EventTypeChoices.NOTIFICATION,
            log=comment,
            pull_request=pull_request,
            datetime=datetime.today()
        )

    event.save()
