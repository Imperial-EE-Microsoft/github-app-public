from django.shortcuts import render
from django.conf import settings
import jwt
import time 

# Create your views here.
# webhook_handler/views.py
import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from github import Github, GithubIntegration
from dotenv import load_dotenv
from django.conf import settings
import logging
from translate.models import Repository, MarkdownFile, LastCommit, PullRequest
from translate.helpers import *
from translate.views import (
    get_langs_fonts_codes_from_config
)



logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


APP_ID = settings.APP_ID
WEBHOOK_SECRET = settings.WEBHOOK_SECRET
ENTERPRISE_HOSTNAME = None
MESSAGE_FOR_NEW_PRS = open("./message.md", "r").read()

def generate_jwt():

    app_id = settings.APP_ID

    private_key_path = settings.PRIVATE_KEY_PATH
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    private_key_path = os.path.join(repo_root, private_key_path)
    with open(private_key_path, 'r') as key_file:
        private_key = key_file.read()
    
    # Generate the JWT
    now = int(time.time())
    payload = {
        'iat': now,
        'exp': now + (10 * 60),  # Token is valid for 10 minutes
        'iss': app_id
    }
    encoded_jwt = jwt.encode(payload, private_key, algorithm='RS256')
    return encoded_jwt

@csrf_exempt
def webhook(request):
    if request.method == "POST":
        event = request.headers.get("X-GitHub-Event")
        payload = json.loads(request.body)
        
        logger.info(f"Event: {event}")
        
        
        # If install event, handle it
        if event == "installation":
            action = payload.get("action")
            if action == "created":
                handle_install_event(payload)
            elif action == "deleted":
                handle_uninstall_event(payload)
            return JsonResponse({"status": "ok"})        

        # The remaining events require github user id and repo id. Do a condition check
        try:
            github_user_id = payload["repository"]["owner"]["name"]
        except:
            try:
                github_user_id = payload["repository"]["owner"]["login"]
            except:
                print("Warning: Github user id not found")
        repo_id = payload["repository"]["id"]
        
        translation_in_progress = Repository.objects.get(repo_id=repo_id, owner_name=github_user_id).translation_in_progress
        print("Translation in progress: ", translation_in_progress)
        
        if translation_in_progress == True:
            print("Ignore")
            return JsonResponse({"error": "Translation in progress"}, status=400)
        
        monitored = Repository.objects.get(repo_id=repo_id, owner_name=github_user_id).monitored
        print("Repo monitoring status: ", monitored)
        
        if monitored == False:
            print("Repo not being monitored! Ignore")
            return JsonResponse({"error": "Repository not being monitored"}, status=400)
        
        # If conditions met, handle the event
        if event == "push":
            branch = payload.get("ref", "").split("/")[-1]
            if branch == "main":
                handle_push_event(payload)
            else:
                logger.info(f"push from {branch} is ignored as it is not main branch")
        
        elif event == "pull_request" and payload.get("action") == "closed":
            handle_pull_request_close_event(payload)

        return JsonResponse({"status": "ok"})
    return JsonResponse({"status": "invalid request"}, status=400)


# refresh the db with newly fetched repos that the bot can access
@csrf_exempt
def refresh_installed_repos(request):
    if request.method == "POST":
        logger.info("generating jwt token")
        jwt_token = generate_jwt()  # Assuming this function is properly defined
        logger.info("jwt token generated")

        # List installations for the GitHub App
        installations_url = "https://api.github.com/app/installations"
        headers = {
            'Authorization': f'Bearer {jwt_token}',
            'Accept': 'application/vnd.github.machine-man-preview+json'
        }
        installations_response = requests.get(installations_url, headers=headers)
        installations = installations_response.json()

        latest_repos = set()
        current_repos = set(Repository.objects.values_list('repo_id', 'owner_name', 'repo_name'))
        print(current_repos)

        for installation in installations:
            # Generate an installation access token
            installation_id = installation['id']
            token_url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
            token_response = requests.post(token_url, headers=headers)
            access_token = token_response.json().get('token', '')

            # Fetch repositories for the installation
            repos_url = installation['repositories_url']
            repo_headers = {
                'Authorization': f'token {access_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            repos_response = requests.get(repos_url, headers=repo_headers)
            repositories = repos_response.json()['repositories']


            for repo in repositories:
                owner_name, repo_name = repo['full_name'].split('/')
                latest_repos.add((repo['id'], owner_name, repo_name))
        
        
        additions = latest_repos - current_repos
        deletions = current_repos - latest_repos
        
        for repo_id, owner_name, repo_name in additions:
            Repository.objects.create(
                repo_id=repo_id,
                owner_name=owner_name,
                repo_name=repo_name,
                monitored=False
            )

        for repo_id, owner_name, repo_name in deletions:
            Repository.objects.filter(repo_id=repo_id).filter(repo_name=repo_name).delete()


            # # Synchronize the database with the fetched repositories
            # existing_repo_ids = set(Repository.objects.values_list('repo_id', flat=True))
            # fetched_repo_ids = set(fetched_repos.keys())

            # # Add new repositories
            # new_repos = fetched_repo_ids - existing_repo_ids
            # for repo_id in new_repos:
            #     repo = fetched_repos[repo_id]
            #     owner_name, repo_name = repo['full_name'].split('/')
            #     Repository.objects.create(
            #         repo_id=repo_id,
            #         owner_name=owner_name,
            #         repo_name=repo_name,
            #         monitored=False
            #     )

            # # Remove repositories that are no longer present
            # removed_repos = existing_repo_ids - fetched_repo_ids
            # Repository.objects.filter(repo_id__in=removed_repos).delete()

        return JsonResponse({"status": "installation refresh processed"})
    return JsonResponse({"status": "invalid request"}, status=400)


    #     for installation in installations:
    #         # Generate an installation access token
    #         installation_id = installation['id']
    #         token_url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    #         token_response = requests.post(token_url, headers=headers)
    #         access_token = token_response.json().get('token', '')

    #         # Fetch repositories for the installation
    #         repos_url = installation['repositories_url']
    #         repo_headers = {
    #             'Authorization': f'token {access_token}',
    #             'Accept': 'application/vnd.github.v3+json'
    #         }
    #         repos_response = requests.get(repos_url, headers=repo_headers)
    #         # repositories = repos_response.json().get('repositories', [])
    #         fetched_repos = {repo['id']: repo for repo in repos_response.json().get('repositories', [])}
        
    #         print("fetched repos: ", fetched_repos)
            
            
    #         account = installation.get("account", {})
    #         # username = account.get("login", "unknown")
    #         # account_type = account.get("type", "User")  # Check the type of account
            
            

    #         # Synchronize the database with the fetched repositories
    #         existing_repo_ids = set(Repository.objects.values_list('repo_id', flat=True))
    #         fetched_repo_ids = set(fetched_repos.keys())

    #         # Add new repositories
    #         new_repos = fetched_repo_ids - existing_repo_ids
    #         print("new repos: ", new_repos)
    #         for repo_id in new_repos:
    #             repo = fetched_repos[repo_id]
    #             owner_name, repo_name = repo['full_name'].split('/')
    #             Repository.objects.create(
    #                 repo_id=repo_id,
    #                 owner_name=owner_name,
    #                 repo_name=repo_name,
    #                 monitored=False
    #             )

    #         # Remove repositories that are no longer present
    #         removed_repos = existing_repo_ids - fetched_repo_ids
    #         Repository.objects.filter(repo_id__in=removed_repos).delete()

    #     return JsonResponse({"status": "installation refresh processed"})
    # return JsonResponse({"status": "invalid request"}, status=400)


def handle_pull_request_close_event(payload):

    action = payload.get("action")
    repo_id = payload['repository']['id']
    pull_request = payload.get("pull_request", {})
    repository_info = pull_request.get("base", {}).get("repo", {})
    repo_name = repository_info.get("name")
    github_user_id = repository_info.get("owner", {}).get("login")
    pr_id = pull_request.get("id")
    access_token = get_github_access_token(github_user_id)

    try:
        # Find the repository and pull request
        repository = Repository.objects.get(repo_id = repo_id)
        pull_request_record = PullRequest.objects.get(repo=repository)

        # Check if the pull request ID matches
        if pull_request_record.pull_request_id == str(pr_id):
            # Update the pull request record
            pull_request_record.pull_request_state = "closed"
            pull_request_record.pull_request_id = ""
            pull_request_record.save()

            print(f"PR #{pr_id} in repo {repo_name} is closed")
        else:
            print(
                f"PR ID mismatch: expected {pull_request_record.pull_request_id}, got {pr_id}"
            )

    except (Repository.DoesNotExist, PullRequest.DoesNotExist) as e:
        print(f"Error: {e}")


def handle_install_event(payload):
    installation = payload.get("installation", {})
    repositories = payload.get("repositories", [])
    account = installation.get("account", {})
    username = account.get("login", "unknown")
    account_type = account.get("type", "User")  # Check the type of account
    # repo_id = payload['repository']['id']


    logger.info(f"{account_type}{username}'s{repositories}is added in Repository database")

    for repo in repositories:
        owner_name, repo_name = repo['full_name'].split('/')
        Repository.objects.update_or_create(
            repo_id = repo['id'],
            owner_name = owner_name,
            repo_name = repo_name,
            monitored = False
        )
        

def handle_uninstall_event(payload):
    installation = payload.get("installation", {})
    account = installation.get("account", {})
    username = account.get("login", "unknown")
    account_type = account.get("type", "User")  # Check the type of account
    repo_id = payload['repository']['id']

    # Delete repositories associated with the uninstalled account
    Repository.objects.filter(repo_id = repo_id).delete()
    logger.info(f"Repositories for repo with id {repo_id} have been deleted")

def handle_push_event(payload):
    logger.info("Received push event payload")

    # update_markdownfile(payload)
    new_commit_sha = payload["after"]
    repo_name = payload["repository"]["name"]
    owner_github_id = payload["repository"]["owner"]["name"]
    owner_type = payload["repository"]["owner"]["type"] 

    access_token = get_github_access_token(owner_github_id)
    g = Github(access_token)
    repo = g.get_user(owner_github_id).get_repo(repo_name)
    repo_id = payload["repository"]["id"]
    repo_full_name = f"{owner_github_id}/{repo_name}"

    
    repository = Repository.objects.get(
        repo_id = repo_id
    )

    pull_request_record = PullRequest.objects.get(repo=repository)
    last_commit_records = LastCommit.objects.filter(repo=repository).order_by('-timestamp')
    if len(last_commit_records) > 0:
        last_commit_record = last_commit_records[0]
    else:
        raise Exception("No last commit record found")
    last_commit_sha = last_commit_record.commit_id

    languages, fontnames, languages_codes = get_langs_fonts_codes_from_config(repo)
    
    #-------------------------------------------------------------------#
    #  Removed feature:
    #   - Do not update main branch commits until pull request is closed
    #---------------------------#
    
    # if pull_request_record.pull_request_state != "closed":
    #     logger.info("commit ignored because pull request still exist")
    # 
    if get_pr_block_setting_from_config(repo):
        logger.info("commit processing")
    else:
    
        
        merge_branches(
            repo, 
            base_branch="co-op-translator", 
            head_branch="main"
        )
        diff_files = get_commit_diff(
            access_token, repo_name, owner_github_id, last_commit_sha, new_commit_sha
        )
        translate_and_update_files(
            diff_files, 
            repo, 
            languages,
            languages_codes,
            fontnames
        )
        create_pull_request(
            access_token, 
            repo_id,
            repo_full_name,
            head_branch="co-op-translator", 
            base_branch="main"
        )

    update_lastcommit(payload)


def update_lastcommit(payload):
    latest_commit = payload["commits"][0]
    repo_id = payload["repository"]["id"]

    repo, created = Repository.objects.update_or_create(
        repo_id = repo_id
    )
    commit_data = {
        "commit_id": latest_commit["id"],
        "author": latest_commit["author"]["name"],
        "message": latest_commit["message"],
        "timestamp": latest_commit["timestamp"],
    }

    # Update or create the LastCommit entry
    last_commit, created = LastCommit.objects.update_or_create(
        repo=repo, defaults=commit_data
    )

    if created:
        print("A new LastCommit record was created.")
    else:
        print("The existing LastCommit record was updated.")
    print(commit_data)

    # python_script_path = os.path.abspath('C:/Users/27846/Desktop/Projects/github-app/python_script/twitter.py')
    # subprocess.run(['python', python_script_path], check=True)


def update_markdownfile(payload):
    github_user_id = payload["repository"]["owner"]["login"]
    repo_name = payload["repository"]["name"]
    access_token = get_github_access_token(github_user_id)
    # store_markdown_file(access_token, github_user_id, repo_name)
    