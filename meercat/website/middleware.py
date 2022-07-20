from django.urls import resolve
from database.models import EventLog

import json
from datetime import datetime
#import traceback

class EventMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        return response
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.user.is_staff:
            return None

        uri = request.build_absolute_uri()
        view_name = resolve(request.path_info).url_name
        user = request.user

        eventLog = EventLog(
            uri=uri, 
            view_name=view_name, 
            view_args=view_args, 
            view_kwargs=view_kwargs, 
            user=user, 
            event_type=EventLog.EventTypeChoices.FEATURE,
            datetime=datetime.today()
        )

        eventLog.save()

    def process_exception(self, request, exception):
        if request.user.is_staff:
            return None

        uri = request.build_absolute_uri()
        log = str(exception)
        # To record a traceback use following line instead (uncomment traceback import)
        #log = ''.join(traceback.format_exception(exception))
        user = request.user

        eventLog = EventLog(
            uri=uri,
            log=log,
            user=user,
            event_type=EventLog.EventTypeChoices.ERROR,
            datetime=datetime.today()
        )

        eventLog.save()
