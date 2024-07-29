from django.shortcuts import render, redirect
import os
import json
import logging
import requests
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import GitHubToken
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from github import Github

# load_dotenv('./../../env')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

CLIENT_ID = settings.CLIENT_ID
CLIENT_SECRET = settings.CLIENT_SECRET
SERVER_URL = settings.SERVER_URL
CALLBACK_URL = f"{SERVER_URL}/auth/github/callback"

print("CALLBACK_URL: ", CALLBACK_URL)

# Login with GitHub view
def login_with_github(request):
    github_auth_url = f"https://github.com/login/oauth/authorize?client_id={CLIENT_ID}&redirect_uri={CALLBACK_URL}"
    return HttpResponseRedirect(github_auth_url)


# GitHub OAuth callback view
@csrf_exempt
def github_callback(request):
    code = request.GET.get("code")
    if not code:
        return JsonResponse({"error": "Code not found in request"}, status=400)

    token_url = "https://github.com/login/oauth/access_token"
    token_data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": CALLBACK_URL,
    }
    headers = {"Accept": "application/json"}
    token_response = requests.post(token_url, data=token_data, headers=headers)
    token_json = token_response.json()

    if "access_token" not in token_json or "refresh_token" not in token_json:
        return JsonResponse({"error": "Failed to get tokens"}, status=400)

    access_token = token_json["access_token"]
    refresh_token = token_json["refresh_token"]
    user_info = get_user_info(access_token)

    github_id = user_info["login"]
    github_account_type = user_info["type"]

    GitHubToken.objects.update_or_create(
        github_id=github_id,
        defaults={"access_token": access_token, "refresh_token": refresh_token},
    )
    request.session["access_token"] = access_token
    request.session["github_id"] = github_id
    request.session["user_info"] = user_info
    request.session["github_account_type"] = github_account_type

    # Redirect to home after successful login
    return redirect("home")


# Helper function to get user info
# -----------------------------------------------------------------------------
def get_user_info(token):
    user_url = "https://api.github.com/user"
    headers = {"Authorization": f"token {token}", "Accept": "application/json"}
    user_response = requests.get(user_url, headers=headers)
    return user_response.json()


# retrieve user repositories
def get_user_repositories(token):
    repos_url = "https://api.github.com/user/repos"
    headers = {"Authorization": f"token {token}", "Accept": "application/json"}
    repos_response = requests.get(repos_url, headers=headers)
    return repos_response.json()


# see if the user is logged in
def check_github_logged_in(request):
    try:
        github_id = request.session.get("github_id")
        if not github_id:
            return JsonResponse({"error": "No GitHub session available"}, status=403)

        # Fetch the token from the database
        token = GitHubToken.objects.get(github_id=github_id)
        user_info = get_user_info(token.access_token)
        


        return JsonResponse(
            {"message": "API access successful", "user_info": user_info, "github_user_id": github_id, "github_account_type": user_info["type"]}
        )
    except GitHubToken.DoesNotExist:
        return JsonResponse({"error": "No token found for user"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

