import os
import requests
from dotenv import load_dotenv
from django.conf import settings
from django.contrib.auth.models import User

load_dotenv(settings.BASE_DIR / '.env')

def user_in_meercat(user):
    return User.objects.filter(email=user['email']).exists()

def get_meercat_user(user):
    if not user_in_meercat(user):
        print('email', user['email'], 'exists:', User.objects.filter(email=user['email']))
        raise Exception('No such user', 'The email does not match any meercat user\'s email')

    return User.objects.get(email=user['email'])

def get_access_token(code):
    access_token_url = 'https://github.com/login/oauth/access_token'
    headers = { 'Accept': 'application/json' }
    payload = {
        'client_id': settings.GH_CLIENT_ID,
        'client_secret': os.environ['GH_CLIENT_SECRET'],
        'code': code,
    }
    
    response = requests.post(access_token_url, data=payload, headers=headers)
    responses = response.json()

    if responses.get('error', False):
        raise Exception(responses.get('error'), responses.get('error_description'))

    return responses['access_token']

def delete_access_token(access_token):
    delete_access_token_url = f'https://github.com//applications/{settings.GH_CLIENT_ID}/token'
    headers = { 'Accept': 'application/vnd.github.v3+json' }
    payload = {
        'access_token': access_token,
    }

    response = requests.delete(delete_access_token_url, data=payload, headers=headers)

    if responses.status_code == 422:
        return False

    return True

def get_gh_user(access_token):
    user_url = 'https://api.github.com/user'
    headers = {
        'Authorization': f'token {access_token}',
        'Accept': 'application/json',
    }

    response = requests.get(user_url, headers=headers)

    if response.status_code == 401:
        raise Exception('Unauthorized', 'Bad Credentials')

    try:
        responses = response.json()
    except Exception as e:
        print('Failed to parse JSON', str(e))

    print(responses)

    return responses


def get_user_repos(access_token):
    headers = {
        'Authorization': f'token {access_token}',
        'Accept': 'application/vnd.github.v3+json',
    }
    repos_url = 'https://api.github.com/user/repos'

    response = requests.get(repos_url, headers=headers)
    responses = response.json()
    return responses
