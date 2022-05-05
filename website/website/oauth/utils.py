import os
import requests
from django.conf import settings


def get_access_token(code):
  access_token_url = 'https://github.com/login/oauth/access_token'
  payload = {
    'client_id': settings.GH_CLIENT_ID,
    'client_secret': os.environ['GH_CLIENT_SECRET'],
    'code': code,
  }
  headers = {
    'Accept': 'application/json'
  }

  response = requests.post(access_token_url, data=payload, headers=headers)
  responses = response.json()
  return responses['access_token']


def get_user(access_token):
  user_url = 'https://api.github.com/user'
  headers = {
    'Authorization': f'token {access_token}',
    'Accept': 'application/json',
  }

  response = requests.get(user_url, headers=headers)
  responses = response.json()
  return responses
