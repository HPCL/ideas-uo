from django.shortcuts import render, redirect
from django.conf import settings

from .utils import get_access_token, get_user, get_user_repos


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


def authorize(request):

    oauth_url = 'https://github.com/login/oauth/authorize'
    redirect_uri = 'http://sansa.cs.uoregon.edu:8888/oauth/user'

    context = {
      'authorize_url': f'{oauth_url}/?client_id={settings.GH_CLIENT_ID};redirect_uri={redirect_uri};scope=repo',
    }

    return render(request, 'oauth/authorize.html', context)
