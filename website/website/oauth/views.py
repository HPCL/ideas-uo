from django.shortcuts import render, redirect
from django.conf import settings
import pprint

from .utils import get_access_token, get_user


def user(request):
    code = request.GET.get('code')

    if not code:
      print('error code')
      request.session['alert_message'] = 'There was a problem logging in'
      request.session['alert_type'] = 'danger'
      return redirect('authorize')

    try:
      access_token = get_access_token(code)
    except:
      request.session['alert_message'] = 'There was a problem reaching GitHub'
      request.session['alert_type'] = 'danger'
      return redirect('authorize')

    try:
      user = get_user(access_token)
    except:
      print('error user')
      request.session['alert_message'] = 'could not get user data'
      request.session['alert_type'] = 'danger'
      return redirect('authorize')

    pp = pprint.PrettyPrinter(indent=2)

    return render(request, 'oauth/user.html', {'user': pp.pformat(user)}) 


def authorize(request):
    alert_message = request.session.get('alert_message', False)
    if alert_message:
      del request.session['alert_message']

    alert_type = request.session.get('alert_type', False)
    if alert_type:
      del request.session['alert_type']

    oauth_url = 'https://github.com/login/oauth/authorize'
    redirect_uri = 'http://127.0.0.1:8000/oauth/user'

    context = {
      'authorize_url': f'{oauth_url}/?client_id={settings.GH_CLIENT_ID};redirect_uri={redirect_uri}',
      'alert_message': alert_message,
      'alert_type': alert_type
    }

    return render(request, 'oauth/authorize.html', context)
