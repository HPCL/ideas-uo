from django.shortcuts import render, redirect
from django.conf import settings

from .utils import get_access_token, get_user, get_user_repos
from .forms import RegistrationForm
from django.core.mail import send_mail

def user(request):
    code = request.GET.get('code')

    if not code:
        return redirect('authorize')

    try:
        access_token = get_access_token(code)
        user = get_user(access_token)
        repos = get_user_repos(access_token)
    except:
        return redirect('authorize')

    return render(request, 'oauth/user.html', {'user': user, 'repos': repos}) 

def register(request):

    if request.method == 'POST':

        form = RegistrationForm(request.POST)
        if form.is_valid():
            name = request.POST['name']
            email = request.POST['email']
            message = request.POST['message']

            subject = 'MeerCAT user registration'
            message = f'Hi,\n\n{name} would like to register for MeerCAT with the email {email} and the following message:\n\n{message}'
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

    oauth_url = 'https://github.com/login/oauth/authorize'
    redirect_uri = 'http://sansa.cs.uoregon.edu:8888/oauth/user'

    context = {
      'authorize_url': f'{oauth_url}/?client_id={settings.GH_CLIENT_ID};redirect_uri={redirect_uri};scope=repo',
    }

    return render(request, 'oauth/authorize.html', context)
