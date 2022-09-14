from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail


def index(request):
    return render(request, 'mainsite/index.html')

def about(request):
    return render(request, 'mainsite/about.html')

