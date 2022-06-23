from dotenv import load_dotenv
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import login

load_dotenv(settings.BASE_DIR / '.env')

def authenticate(request, gh_user):
    # returns wether authentication succeded
    meercat_user = None

    if gh_user['email'] and User.objects.filter(githubcredentials__email=gh_user['email']).exists():
        meercat_user = User.objects.get(githubcredentials__email=gh_user['email'])

    if gh_user['login'] and User.objects.filter(githubcredentials__email=gh_user['login']).exists():
        meercat_user = User.objects.get(githubcredentials__login=gh_user['login'])

    if meercat_user is not None:
        login(request, meercat_user)
        return True
    else:
        return False