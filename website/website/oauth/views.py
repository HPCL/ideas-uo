from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponse
import pprint

from .utils import get_access_token, get_user

def user(request):
  try:
    code = request.GET.get('code')

    if not code:
      # push error to session errors, redirect to authorize
      return HttpResponse('No code')

    access_token = get_access_token(code)
    user = get_user(access_token)

    if not user:
      return HttpResponse('No access code')

    pp = pprint.PrettyPrinter(indent=2)

    return render(request, 'oauth/user.html', {'user': pp.pformat(user)}) 
  except Exception as e:
    return HttpResponse(e)
  

def authorize(request):
    oauth_url = 'https://github.com/login/oauth/authorize'
    redirect_uri = 'http://127.0.0.1:8000/oauth/user'

    context = {
      'authorize_url': f'{oauth_url}/?client_id={settings.GH_CLIENT_ID};redirect_uri={redirect_uri}',
    }

    return render(request, 'oauth/authorize.html', context)
