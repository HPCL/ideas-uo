from django.core.management.base import BaseCommand
from django.db.models import Q

from datetime import datetime
from database.utilities import comment_pullrequest
from database.models import EventLog, PullRequest
from dashboard.views import first_responder_function
from database.utilities import comment_pullrequest

class Command(BaseCommand):
    help = 'Leaves a comment on pull requests that are new or on previously failed comments'

    def handle(self, *args, **options):
        print('Django command working')
        included_repos=['anl_test_repo']
        new_pr_or_failed_comments = Q(eventlog__pull_request__isnull=True) | Q(eventlog__event_type=EventLog.EventTypeChoices.NOTIFICATION_FAIL)
        pull_requests = PullRequest.objects.filter(new_pr_or_failed_comments, project__name__in=included_repos, created_at__gte=datetime(2022, 7, 18))

        if not pull_requests.exists():
            print("No notifications to send")

        for pull_request in pull_requests.all():
            print("PR number:", pull_request.number)
        
            comment = first_responder_function(pull_request.project, pull_request)[0]
            print("------------")
            if comment:
                comment_pullrequest(pull_request, comment)
                print("commented")
            else:
                event = EventLog(
                    event_type=EventLog.EventTypeChoices.NO_NOTIFICATION,
                    pull_request=pull_request,
                    datetime=datetime.today()            
                )
                print("don't bug me")

            print("------------")