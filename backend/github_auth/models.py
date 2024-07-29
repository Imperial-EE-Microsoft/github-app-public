from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import requests


class GitHubToken(models.Model):
    github_id = models.CharField(
        max_length=255, unique=True, default="default_github_id"
    )
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255, default="-1")

    def refresh_access_token(self):
        """
        Refresh the access token using the refresh token
        """
        url = "https://github.com/login/oauth/access_token"
        data = {
            "client_id": settings.CLIENT_ID,
            "client_secret": settings.CLIENT_SECRET,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }
        headers = {"Accept": "application/json"}
        response = requests.post(url, data=data, headers=headers)

        if response.status_code == 200:
            token_info = response.json()
            self.access_token = token_info.get("access_token")
            self.refresh_token = token_info.get("refresh_token", self.refresh_token)
            self.save()
            return self.access_token
        else:
            raise Exception(f"Failed to refresh token: {response.content}")
