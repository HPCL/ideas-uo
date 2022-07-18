from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('authorize_gitlab/', views.authorize_gitlab, name='authorize_gitlab'),
    path('gitlab_callback/', views.gitlab_callback, name='gitlab_callback'),
    path('authorize_github/', views.authorize_github, name='authorize_github'),
    path('github_callback/', views.github_callback, name='github_callback'),
]