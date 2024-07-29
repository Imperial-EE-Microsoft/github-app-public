from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.http import JsonResponse
from .models import LastCommit, Repository, MarkdownFile, PullRequest, MonitoredRepository
from django.conf import settings
from .helpers import *
import logging
from django.views.decorators.csrf import csrf_exempt
from .image_translate import translate_image_content


import yaml
import pycountry
from github import Github
from django.http import JsonResponse

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@csrf_exempt
def translate_init(request):
    """
    1. Invite robot to join the GitHub repo
    """
    if request.method == "POST":
        data = json.loads(request.body)
        github_user_id = data.get("github_id")
        repo_id = data.get('repo_id')
        

        
        access_token = request.META.get('HTTP_AUTHORIZATION', None)
        if access_token:
            access_token = access_token.replace("Bearer ", "", 1)  # Removes "Bearer " if present


    else:
        return JsonResponse({"error": "Invalid request method"}, status=400)


    if not github_user_id or not repo_id:
        return JsonResponse({"error": "Missing required parameters"}, status=400)

    try:
        repository = Repository.objects.get(repo_id=repo_id)
    except Repository.DoesNotExist:
        print(f"Repository with ID {repo_id} does not exist")
        print(f"All repository ids: {Repository.objects.values_list('repo_id', flat=True)}")
        return JsonResponse({"error": "Repository not found"}, status=404)

    repo_name = repository.repo_name
    repo_owner = repository.owner_name
    repo_full_name = f"{repo_owner}/{repo_name}"


    robot_user_id = settings.ROBOT_USER_ID
    robot_pat = settings.ROBOT_PAT

    send_invitation(
        access_token=access_token,
        repo_full_name=repo_full_name,
        invitee_github_id=robot_user_id,
    )
    accept_invitations(robot_pat)
    return JsonResponse({"result": "success"})

@csrf_exempt
# returns all orgs that a github user is a part of.
def get_user_orgs(access_token):
    headers = {"Authorization": f"token {access_token}"}
    response = requests.get("https://api.github.com/user/orgs", headers=headers)
    response.raise_for_status()
    return [org['login'] for org in response.json()]


@csrf_exempt
def dashboard_get_repos(request):
    """
    Get a list of all repositories for the current login user from the Django database, including their monitored status.
    Also returns repositories belonging to orgs of the current user that are detected by the Co-Operator GitHub app
    """
    
    github_user_id = request.headers.get("X-Github-User-Id")
    # access_token = request.headers.get("X-Github-Access-Token")
    access_token = request.META.get('HTTP_AUTHORIZATION', None)
    if access_token:
        access_token = access_token.replace("Bearer ", "", 1)  # Removes "Bearer " if present
    else:
        access_token = request.session.get("access_token")
    # print(f"access_token: {access_token}")
    
    if not github_user_id or not access_token:
        return JsonResponse({"error": "User not logged in or token not provided"}, status=401)
    
    try:
        orgs = get_user_orgs(access_token)
    except requests.RequestException as e:
        return JsonResponse({"error": "Failed to fetch user organisations"}, status=500)

    # Query the database for repositories associated with the GitHub user ID and organisations
    repositories = Repository.objects.filter(owner_name__in=[github_user_id] + orgs)

    repo_list = [{
        "repo_name": repo.repo_name,
        "repo_id": repo.repo_id,
        "owner_name": repo.owner_name,
        "repo_url": f"https://github.com/{repo.owner_name}/{repo.repo_name}",
        "monitored": repo.monitored
    } for repo in repositories]


    # print('#### here')
    response_data = {
        "repositories": repo_list,
    }
    return JsonResponse(response_data, status=200)

@csrf_exempt
def set_monitoring_status(request, repo_id, status):
    """
    Set the monitoring status of a repository
    """
    github_user_id = request.session.get("github_id")
    github_account_type = request.session.get("github_account_type")
    access_token = request.session.get("access_token")

    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    try:
        repo = Repository.objects.get(repo_id=repo_id)
        try: 
            if status:
                #  translation setup involves creating a branch named 'co-op-translator'
                branch_name = 'co-op-translator'
                repo.translation_in_progress = True
                repo.save()
                api_url = f"http://{request.get_host()}/translate/init/"
                response = requests.post(api_url, headers=headers, json={'repo_id': repo_id, 'github_id': github_user_id, 'github_account_type': github_account_type})
                if response.status_code != 200:
                    return JsonResponse({"error": "Failed to call translation init"}, status=500)
                
                api_url = f"http://{request.get_host()}/translate/translate/"
                response = requests.post(api_url, headers=headers, json={'repo_id': repo_id, 'github_id': github_user_id, 'github_account_type': github_account_type})
                if response.status_code != 200:
                    return JsonResponse({"error": "Failed to call translation API"}, status=500)

                # Construct the URL for the branch
                branch_url = f"https://github.com/{github_user_id}/{repo.repo_name}/tree/{branch_name}"

                repo.monitored = status
                repo.translation_in_progress = False
                repo.save()
                return JsonResponse({"status": "success", "message": "Monitoring turned on successfully.", "branch_url": branch_url}, status=200)

            else:
                # Code to handle turning off monitoring
                robot_pat = settings.ROBOT_PAT
                repo_full_name = f"{github_user_id}/{repo.repo_name}"
                try:
                    delete_github_branch(robot_pat, repo_id, repo_full_name, "co-op-translator")
                except:
                    print('ERROR: Failed to delete branch')
                repo.translation_in_progress = False
                repo.monitored = status
                repo.save()
                return JsonResponse({"status": "success", "message": "Monitoring turned off successfully."}, status=200)
        except:
            repo.translation_in_progress = False
            repo.save()
            return JsonResponse({"error": str(e)}, status=500)
            
    except Repository.DoesNotExist as e:
        logger.error(e)
        return JsonResponse({"error": "Repository not found"}, status=404)
    except Exception as e:
        logger.error(e)
        return JsonResponse({"error": str(e)}, status=500)


    
@csrf_exempt
def set_monitoring_true(request, repo_id):
    return set_monitoring_status(request, repo_id, True)

@csrf_exempt
def set_monitoring_false(request, repo_id):
    return set_monitoring_status(request, repo_id, False)







def get_langs_fonts_codes_from_config(repo):
    """
    Fetches the language list from co-op-config.yml in the root of the repo.
    If the file does not exist, initializes it with default languages ['zh', 'fr']
    and pushes the new config file. Also returns a flag indicating if defaults were used.
    
    It returns a tuple of (langs, fonts, codes), where:
    langs is list of full names of the languages, like ['Chinese', 'French']
    fonts is list of font names, like ['"NotoSansCJK-Medium.ttc"', 'NotoSans-Medium.ttf']
    codes is list of ISO language codes, like ['cn', 'fr']
    
    In these lists, any invalid language codes found in config are omitted.
    """
    
    try:
        contents = repo.get_contents("co-op-config.yml")
        config_yaml = yaml.safe_load(contents.decoded_content)
        languages_codes_from_config = config_yaml.get('languages', [])
    except Exception as e:
        default_config = {'languages': ['zh', 'fr'], 'docs_directory': 'docs/'}
        print('co-op-config.yml not found, creating default config with sample languages: ', default_config['languages'])
        default_content_yaml = yaml.safe_dump(default_config)
        repo.create_file("co-op-config.yml", "Create default co-op-config.yml", default_content_yaml, branch="main")
        languages_codes_from_config = default_config['languages']
        
    valid_languages = []
    valid_codes = []
    fontnames = []
    
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    with open(os.path.join(repo_root, "font_language_mappings.yml"), "r") as file:
        mappings = yaml.safe_load(file)
    
    for code in languages_codes_from_config:
        language = pycountry.languages.get(alpha_2=code)
        if language:
            valid_languages.append(language.name)
            valid_codes.append(code)
            fontname = mappings.get(code, {'name': '', 'font': '"NotoSans-Medium.ttf"'})['font']
            fontnames.append(fontname)

        else:
            print(f"Unknown code: {code}",)
            
    return valid_languages, fontnames, valid_codes

        


        

        
    
    

@csrf_exempt
def translate_endpoint(request):
    """
    Endpoint to translate markdown files in a repository, and create a pull request with the changes.
    """
    
    if request.method == "POST":
        data = json.loads(request.body)
        github_user_id = data.get("github_id")
        github_account_type = data.get("github_account_type")
        repo_id = data.get('repo_id')
        access_token = request.META.get('HTTP_AUTHORIZATION', None)
        if access_token:
            access_token = access_token.replace("Bearer ", "", 1)  # Removes "Bearer " if present

    else:
        return JsonResponse({"error": "Invalid request method"}, status=400)
    if not repo_id:
        return JsonResponse({'error': 'repo_id parameter is missing'}, status=400)
    if not github_user_id or not github_account_type:
        return JsonResponse({'error': 'GitHub user credentials are missing'}, status=401)

    robot_pat = settings.ROBOT_PAT
    g = Github(robot_pat)
    repository = Repository.objects.get(repo_id=repo_id)
    repo_full_name = f"{repository.owner_name}/{repository.repo_name}"
    repo = g.get_repo(repo_full_name)


    languages, fontnames, languages_codes = get_langs_fonts_codes_from_config(repo)
    
    try:
        delete_github_branch(robot_pat, repo_id, repo_full_name, "co-op-translator")
    except:
        print('ERROR: Failed to delete branch')
    print(f'calling create_github_branch with robot_pat: {robot_pat}, repo_id: {repo_id}, repo_full_name: {repo_full_name}, branch_name: "co-op-translator"')
    create_github_branch(robot_pat, repo_id, repo_full_name, "co-op-translator")

    diff_files = get_all_md_file_paths(repo)
    translate_and_update_files(diff_files, repo, languages, languages_codes, fontnames)
    get_and_store_last_commit(robot_pat, repo_id, repo_full_name)

    create_pull_request(access_token=robot_pat, repo_id=repo_id, repo_full_name=repo_full_name, head_branch="co-op-translator", base_branch="main")
    return JsonResponse({"result": "translate successfully"})


# def test_view(request):
#     access_token = request.session.get("access_token")
#     repo_name = "Github-API-Tester"
#     github_user_id = request.session.get("github_id")
#     path_to_image = "docs/cat1.png"

#     g = Github(access_token)
#     repo = g.get_repo(f"{github_user_id}/{repo_name}")

#     content1 = repo.get_contents(
#         path_to_image,
#         ref="main"
#     ).content
#     content1 = base64.b64decode(content1)

#     repo_full_name = f"{github_user_id}/{repo_name}"

#     # print(repo.full_name)
#     # print(repo_full_name)

#     content2 = get_github_image_content(
#         settings.ROBOT_PAT,
#         repo.full_name,
#         path_to_image, 
#         "main"
#     )
    
#     print(content1 == content2)
#     return JsonResponse({"result": "success"})
#     # return JsonResponse({'message': 'Success'}, status=200)
