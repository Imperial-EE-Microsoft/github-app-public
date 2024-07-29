from django.urls import path
from .views import login_with_github, github_callback, check_github_logged_in

urlpatterns = [
    path(
        "login/", login_with_github, name="login_with_github"
    ),  # URL for initiating GitHub login
    path(
        "callback/", github_callback, name="github_callback"
    ),  # URL for handling GitHub OAuth callback,
    path("status/", check_github_logged_in, name="test_github_api"),
]
