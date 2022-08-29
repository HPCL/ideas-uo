from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views

from dashboard.views import index

urlpatterns = [
    path('', index, name='index'),
    path('dashboard/', include('dashboard.urls')),
    path('oauth/', include('oauth.urls')),
    path('admin/', admin.site.urls),
    path('logout/', auth_views.LogoutView.as_view(template_name='oauth/logout.html'), name='logout')
]
