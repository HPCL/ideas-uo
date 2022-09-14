from dotenv import load_dotenv
from datetime import datetime
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import login
from database.models import EventLog

load_dotenv(settings.BASE_DIR / '.env')

def gh_authenticate(request, gh_user):
    # returns wether authentication succeded
    meercat_user = None

    try:
        if gh_user['login'] and User.objects.filter(profile__gh_login=gh_user['login']).exists():
            meercat_user = User.objects.get(profile__gh_login=gh_user['login'])
        elif gh_user['email'] and User.objects.filter(profile__gh_email=gh_user['email']).exists():
            meercat_user = User.objects.get(profile__gh_email=gh_user['email'])
        
    except KeyError as ke: # In case the response does not have an login key
        event = EventLog(
            event_type=EventLog.EventTypeChoices.ERROR, 
            log=ke,
            datetime=datetime.today()
        )
        meercat_user = None


    if meercat_user is not None:
        login(request, meercat_user)
        return True
    else:
        return False

def gl_authenticate(request, gl_user):
    # returns wether authentication succeded
    meercat_user = None

    print('gl_user["email"]:', gl_user['email'], 'gl_user["username"]:', gl_user['username'])
    print('gl_user:', gl_user)
    print(User.objects.get(profile__gl_username=gl_user['username']))

    try:
        if gl_user['email'] and User.objects.filter(profile__gl_email=gl_user['email']).exists():
            meercat_user = User.objects.get(profile__gl_email=gl_user['email'])
        elif gl_user['username'] and User.objects.filter(profile__gl_username=gl_user['username']).exists():
            meercat_user = User.objects.get(profile__gl_username=gl_user['username'])

    except KeyError as ke: # In case the response does not have an login key
        event = EventLog(
            event_type=EventLog.EventTypeChoices.ERROR, 
            log=ke,
            datetime=datetime.today()
        )
        meercat_user = None

    if meercat_user is not None:
        login(request, meercat_user)
        return True
    else:
        return False