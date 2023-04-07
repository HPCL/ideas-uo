from datetime import datetime
import os

from database.models import EventLog

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class Command(BaseCommand):
    # Refreshes gmail OAuth token by requesting user info

    def handle(self, *args, **options):
        creds = None

        if os.path.exists(settings.BASE_DIR / "token.json"):
            creds = Credentials.from_authorized_user_file(
                settings.BASE_DIR / "token.json",
                [
                    "https://www.googleapis.com/auth/gmail.send",
                    "https://www.googleapis.com/auth/gmail.metadata",
                "https://www.googleapis.com/auth/gmail.readonly",
                ],
            )
        else:
            raise CommandError("Token file not found")

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                raise CommandError("Token could not be refreshed")
            # Save the credentials for the next run
            with open(settings.BASE_DIR / "token.json", "w") as token:
                token.write(creds.to_json())

        try:
            gmail_service = build("gmail", "v1", credentials=creds)
            gmail_service.users().getProfile(userId="uomeercat@gmail.com").execute()

        except HttpError as httpe:
            refresh_token_error = EventLog(
                event_type=EventLog.EventTypeChoices.ERR,
                datetime=datetime.today(),
                log=str(httpe),
            )

            refresh_token_error.save()
