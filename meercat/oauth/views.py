from requests_oauthlib import OAuth2Session
from oauthlib.oauth2.rfc6749.errors import AccessDeniedError
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail

from .utils import gh_authenticate, gl_authenticate
from .forms import RegistrationForm
from dashboard.utilities import gmail_send_message

import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' # This is set so requests-oauthlib does not throw an error over HTTP

gl_redirect_uri='http://127.0.0.1:8000/oauth/gitlab_callback/'
gl_scope = [
    'api',
    'read_user',
    'read_api',
    'read_repository',
    'write_repository',
    'read_registry',
    'write_registry',
    'sudo',
    'openid',
    'profile',
    'email',
]

if settings.OAUTH_DEVELOPMENT:
    # GitLab Development
    gl_client_id = settings.GL_CLIENT_ID_DEV
    gl_client_secret = os.environ['GL_CLIENT_SECRET_DEV']

    # GitHub Development
    gh_client_id = settings.GH_CLIENT_ID_DEV
    gh_client_secret = os.environ['GH_CLIENT_SECRET_DEV']

else:
    gh_client_id = settings.GH_CLIENT_ID
    gh_client_secret = os.environ['GH_CLIENT_SECRET']


def authorize_gitlab(request):
    authorization_base_url = 'https://gitlab.com/oauth/authorize'

    gitlab = OAuth2Session(gl_client_id, scope=gl_scope, redirect_uri=gl_redirect_uri)
    authorization_url, state = gitlab.authorization_url(authorization_base_url)

    request.session['gl_oauth_state'] = state
    return redirect(authorization_url)


def gitlab_callback(request):
    token_url = 'https://gitlab.com/oauth/token'
    gitlab = OAuth2Session(gl_client_id, scope=gl_scope, state=request.GET.get('state'), redirect_uri=gl_redirect_uri)

    try:
        token = gitlab.fetch_token(token_url, client_secret=gl_client_secret,
                               code=request.GET.get('code'))
    except AccessDeniedError as ade:
        print(ade)
        messages.error(request, 'You have denied application access. To log in, please authorize through GitHub.')
        return redirect('login')
    except Exception as ex:
        print(ex)
        messages.error(request, 'There was an error during GitLab authorization. Please contact the meercat team and try again later.')
        return redirect('login')

    request.session['gl_access_token'] = token['access_token']
    gl_user = gitlab.get('https://gitlab.com/api/v4/user').json()
    
    autheitcation_success = gl_authenticate(request, gl_user)
    if autheitcation_success:
        return redirect('index')
    else:
        messages.warning(request, 'Your GitLab account has not been registered in our site. Please register to continue.')
        return redirect('register')


def authorize_github(request):
    authorization_base_url = 'https://github.com/login/oauth/authorize'
    scope = ['repo']

    github = OAuth2Session(gh_client_id, scope=scope)
    authorization_url, state = github.authorization_url(authorization_base_url)

    request.session['gh_oauth_state'] = state
    return redirect(authorization_url)


def github_callback(request):
    token_url = 'https://github.com/login/oauth/access_token'
    github = OAuth2Session(gh_client_id, state=request.session['gh_oauth_state'])

    try:
        token = github.fetch_token(token_url, client_secret=gh_client_secret,
                               authorization_response=request.build_absolute_uri())
    except AccessDeniedError as ade:
        print(ade)
        messages.error(request, 'You have denied application access. To log in, please authorize through GitHub.')
        return redirect('login')
    except Exception as ex:
        print(ex)
        messages.error(request, 'There was an error during GitHub authorization. Please contact the meercat team and try again later.')
        return redirect('login')

    request.session['oauth_token'] = token
    gh_user = github.get('https://api.github.com/user').json()
    
    autheitcation_success = gh_authenticate(request, gh_user)
    if autheitcation_success:
        return redirect('index')
    else:
        messages.warning(request, 'Your GitHub account has not been registered in our site. Please register to continue.')
        print(gh_user)
        request.session['gh_user'] = gh_user
        return redirect('register')


def login(request):
    return render(request, 'oauth/login.html')


def register(request):

    gh_user = request.session.get('gh_user', False)
    if gh_user:
        initial_data = {
            'username': gh_user['login'],
            'email': gh_user['email'],
        }
        del request.session['gh_user']
    else:
        initial_data = {}

    if request.method == 'POST':

        form = RegistrationForm(request.POST, initial=initial_data)
        if form.is_valid():
            name = request.POST['name']
            email = request.POST['personal_email']
            message = request.POST['message']
            username = request.POST['username']

            subject = 'MeerCAT user registration'
            message = f'Hi,\n\n{name} would like to register for MeerCAT as {username} with the email {email} and has the following message:\n\n{message}'
            recipient_list = ['uomeercat@gmail.com', 'jpfloresd.97@gmail.com']

            sent = gmail_send_message(subject, message, sender='uomeercat@gmail.com', recipient_list=recipient_list)
            if sent is None:
                form.add_error(field=None, error='Failed to send message')
                return render(request, 'oauth/registration.html', {'form': form})
            else:
                return render(request, 'oauth/success.html', {'name': name, 'email': email})

    else:
        form = RegistrationForm(initial=initial_data)

    return render(request, 'oauth/registration.html', {'form': form})