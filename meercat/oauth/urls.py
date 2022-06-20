from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login, name='login'),
    path('authorize/', views.authorize, name='authorize'),
    path('register/', views.register, name='register'),
]