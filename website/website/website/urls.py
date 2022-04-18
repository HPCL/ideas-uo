from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('authenticate/', include('oauth.urls')),
    path('admin/', admin.site.urls),
]
