from database.models import EventLog
from datetime import datetime

def save_debug_event(log, json='', pull_request=None, user=None, uri='', view_name=''):

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