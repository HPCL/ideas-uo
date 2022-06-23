from requests_oauthlib import OAuth2Session
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail

from .utils import authenticate
from .forms import RegistrationForm

import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' # This is set so requests-oauthlib does not throw an error over HTTP

client_id = settings.GH_CLIENT_ID
client_secret = os.environ['GH_CLIENT_SECRET']

def authorize_github(request):
    authorization_base_url = 'https://github.com/login/oauth/authorize'

    github = OAuth2Session(client_id)
    authorization_url, state = github.authorization_url(authorization_base_url)

    request.session['oauth_state'] = state
    return redirect(authorization_url)

def callback(request):
    token_url = 'https://github.com/login/oauth/access_token'
    github = OAuth2Session(client_id, state=request.session['oauth_state'])
    token = github.fetch_token(token_url, client_secret=client_secret,
                               authorization_response=request.build_absolute_uri())

    request.session['oauth_token'] = token
    gh_user = github.get('https://api.github.com/user').json()
    
    autheitcation_success = authenticate(request, gh_user)
    if autheitcation_success:
        return redirect('index')
    else:
        messages.warning(request, 'Your GitHub account has not been registered in our site. Please register to continue.')
        return redirect('register')


def login(request):
    return render(request, 'oauth/login.html')


def register(request):

    if request.method == 'POST':

        form = RegistrationForm(request.POST)
        if form.is_valid():
            name = request.POST['name']
            email = request.POST['personal_email']
            message = request.POST['message']

            subject = 'MeerCAT user registration'
            message = f'Hi,\n\n{name} would like to register for MeerCAT as {username} with the email {email} and has the following message:\n\n{message}'
            recipient_list = ['jpfloresd.97@gmail.com']

            sent = send_mail(subject, message, from_email=None, recipient_list=recipient_list)
            if sent == 0:
                form.add_error(field=None, error='Failed to send message')
                return render(request, 'oauth/registration.html', {'form': form})
            else:
                return render(request, 'oauth/success.html', {'name': name, 'email': email})

    else:
        form = RegistrationForm()

    return render(request, 'oauth/registration.html', {'form': form})