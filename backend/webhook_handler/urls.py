from django.urls import path
from .views import webhook, refresh_installed_repos

urlpatterns = [
    path("webhook/", webhook, name="webhook"),
    path("refresh/", refresh_installed_repos, name="refresh_installed_repos"),
]
