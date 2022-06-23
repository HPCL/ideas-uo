from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login, name='login'),
    path('authorize_github/', views.authorize_github, name='authorize_github'),
    path('callback/', views.callback, name='callback'),
    path('register/', views.register, name='register'),
]