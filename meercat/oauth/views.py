from uuid import uuid4
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.contrib.auth import login as auth_login

from .utils import get_access_token, delete_access_token, get_gh_user, get_meercat_user
from .forms import RegistrationForm


def login(request):
    code = request.GET.get('code', False)
    returned_state = request.GET.get('state', False)
    oauth_state = request.session.get('oauth_state', False)
    prev_access_token = request.session.get('access_token', False)

    if prev_access_token:
        try:
            get_gh_user(prev_access_token)
            return redirect('index')
        except Exception as e:
            print(str(e))
            del request.session['access_token']
            messages.warning(request, 'Your session has expired')
            return redirect('authorize')

    if not (code or returned_state or oauth_state) and returned_state != oauth_state:
        print('code:', code, 'returned_state:', returned_state, 'oauth_state:', oauth_state)
        messages.error(request, 'An error occured while trying to authenticate with GitHub')
        return redirect('authorize')

    if not request.session.get('oauth_state', False):
        del request.session['oauth_state']

    try:
        new_access_token = get_access_token(code)
        request.session['access_token'] = new_access_token
        gh_user = get_gh_user(new_access_token)
    except Exception as e:
        print(str(e))
        if request.session.get('access_token', False):
            del request.session['access_token']
        messages.error(request, 'An error occured while trying to authenticate with GitHub')
        return redirect('authorize')

    try:
        meercat_user = get_meercat_user(gh_user)
        auth_login(request, meercat_user)
    except Exception as e:
        print(str(e))
        messages.warning(request, 'Your GitHub account has not been registered in our site. Please register to continue.')
        return redirect('authorize')

    return redirect('index')


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


def authorize(request):
    state = uuid4().hex
    oauth_url = 'https://github.com/login/oauth/authorize'
    redirect_uri = 'http://sansa.cs.uoregon.edu:8888/oauth/login'

    authorize_url = f'{oauth_url}/?state={state};client_id={settings.GH_CLIENT_ID};redirect_uri={redirect_uri};scope=repo'

    context = {
      'authorize_url': authorize_url,
    }

    request.session['oauth_state'] = state

    return render(request, 'oauth/authorize.html', context)
