from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from github import Github, GithubException
from django.shortcuts import redirect
from django.http import JsonResponse
import requests
from .models import LastCommit, Repository, MarkdownFile, PullRequest
from .serializers import *
from django.conf import settings
import base64
from github_auth.models import GitHubToken
import os
from .translate import *
import logging
from .image_translate import translate_image_content
from io import BytesIO
from PIL import Image
import os
import warnings
import hashlib
import time


def get_pr_block_setting_from_config(repo):
    try:
        contents = repo.get_contents("co-op-config.yml")
        config_yaml = yaml.safe_load(contents.decoded_content)
        block = config_yaml.get('update_only_when_pr_closed', False)
    except Exception as e:
        default_config = {'languages': ['zh', 'fr'], 'docs_directory': 'docs/', 'update_only_when_pr_closed': False}
        print('co-op-config.yml not found, creating auto-generated default config with sample languages: ', default_config['languages'])
        default_content_yaml = yaml.safe_dump(default_config)
        default_content_yaml = "\n# This is an auto-generated config file." + default_content_yaml
        repo.create_file("co-op-config.yml", "Auto-generated default co-op-config.yml", default_content_yaml, branch="main")
        block = default_config['update_only_when_pr_closed']

    return block

        

def get_docs_path_from_config(repo):
    try:
        contents = repo.get_contents("co-op-config.yml")
        config_yaml = yaml.safe_load(contents.decoded_content)
        docs_dir = config_yaml.get('docs_directory', 'docs/')
    except Exception as e:
        default_config = {'languages': ['zh', 'fr'], 'docs_directory': 'docs/', 'update_only_when_pr_closed': False}
        print('co-op-config.yml not found, creating auto-generated default config with sample languages: ', default_config['languages'])
        default_content_yaml = yaml.safe_dump(default_config)
        default_content_yaml = "\n# This is an auto-generated config file." + default_content_yaml
        repo.create_file("co-op-config.yml", "Auto-generated default co-op-config.yml", default_content_yaml, branch="main")
        docs_dir = default_config['docs_directory']

    return docs_dir


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def dashboard_initializer(
        access_token, 
        github_user_id, 
        repo_name,
        github_account_type
):
    """
    extract data from a repo, and load all file into database
    """
    # if not access_token or not github_user_id:
    #     return JsonResponse({"error": "Session data not found"}, status=400)

    # repo_data = get_repository_data(access_token, github_user_id, repo_name)
    # repo_full_name = repo_data["full_name"]

    # get_and_store_last_commit(
    #     access_token, 
    #     github_user_id, 
    #     repo_full_name,
    #     github_account_type=github_account_type
    # )
    # get_and_store_repo_data(access_token, github_user_id, repo_name)
    # # store_markdown_file(access_token, github_user_id, repo_name)

    return True


def create_github_branch(
        access_token, 
        repo_id, 
        repo_full_name,
        new_branch_name
    ):
    """
    Creates a new branch in the specified GitHub repository.
    """
    # Authenticate with GitHub using the access token
    g = Github(access_token)
    repo = g.get_repo(repo_full_name)
    
    # Get the latest commit SHA from the main branch
    main_branch = repo.get_branch("main")
    sha = main_branch.commit.sha

    # Create a new branch
    ref = f"refs/heads/{new_branch_name}"
    try:
        repo.create_git_ref(ref, sha)
        return f"Branch '{new_branch_name}' created successfully."
    except Exception as e:
        raise Exception(f"Failed to create new branch: {e.data}")

def delete_github_branch(
        access_token, 
        repo_id,
        repo_full_name, 
        branch_name
    ):
    """
    Deletes a branch in the specified GitHub repository if it exists.
    Does nothing if the branch does not exist.
    """
    g = Github(access_token)
    repo = g.get_repo(repo_full_name)
    
    try:
        ref = repo.get_git_ref(f"heads/{branch_name}")
        ref.delete()
        return "Branch deleted successfully."
    except Exception as e:
        if e.status == 404:
            return "Branch does not exist, nothing to do."
        else:
            raise Exception(f"Failed to delete branch: {e.data}")



def update_github_branch(
    access_token, repo_name, github_user_id, branch, new_content="This is a test update"
):
    base_url = (
        f"https://api.github.com/repos/{github_user_id}/{repo_name}/contents/README.md"
    )
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Get the file SHA
    response = requests.get(f"{base_url}?ref={branch}", headers=headers)
    response.raise_for_status()
    file_info = response.json()
    sha = file_info["sha"]

    # Update the README file
    update_data = {
        "message": "Updating README.md",
        "content": base64.b64encode(new_content.encode()).decode(),
        "sha": sha,
        "branch": branch,
    }

    update_response = requests.put(base_url, json=update_data, headers=headers)
    update_response.raise_for_status()
    return update_response.json()


def create_pull_request(
    access_token,
    repo_id,
    repo_full_name,
    head_branch,
    base_branch="main",
    push_message=None,
):
    """
    Creates a pull request in a GitHub repository.
    
    Returns:
    - dict: Information about the created pull request if successful.
    """
    g = Github(access_token)
    repo = g.get_repo(repo_full_name)

    logger.info(f"pull request create from {head_branch} to {base_branch}")

    if push_message is None:
        push_message = {
            "title": "Localization Update",
            "body": "This PR updates the localization files.",
        }

    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    pulls_url = f"https://api.github.com/repos/{repo_full_name}/pulls"
    payload = {
        "title": push_message["title"],
        "head": head_branch,
        "base": base_branch,
        "body": push_message["body"],
    }

    response = requests.post(pulls_url, headers=headers, json=payload)
    response.raise_for_status()
    pr_data = response.json()
    pr_id = pr_data["id"]

    try:
        repository, created = Repository.objects.get_or_create(
            repo_id = repo_id
        )
        PullRequest.objects.update_or_create(
            repo=repository,
            defaults={"pull_request_state": "open", "pull_request_id": pr_id,},
        )
    except Exception as e:
        print(f"Error saving pull request to database: {e}")

    return pr_data


def get_and_store_last_commit(
        access_token, 
        repo_id,
        repo_full_name
):  
    g = Github(access_token)
    repo = g.get_repo(repo_full_name)

    commits_url = f"https://api.github.com/repos/{repo_full_name}/commits"
    headers = {"Authorization": f"token {access_token}", "Accept": "application/json"}
    commits_response = requests.get(commits_url, headers=headers)
    commits = commits_response.json()

    if not commits:
        raise Exception("No commits found for the repository.")
    else:
        latest_commit = commits[0]
        repo, created = Repository.objects.update_or_create(
            repo_id = repo_id
        )

        commit_data = {
            "repo": repo.id,  
            "commit_id": latest_commit["sha"],
            "author": latest_commit["commit"]["author"]["name"],
            "message": latest_commit["commit"]["message"],
            "timestamp": latest_commit["commit"]["author"]["date"],
        }

        # Use the serializer to validate and save the data
        # serializer = CommitSerializer(data=commit_data)
        # if serializer.is_valid():
        #     serializer.save()
        # else:
        #     print(serializer.errors)
        # problem with the above code using save(): will cause error if commit_id already exists
        # {'repo': [ErrorDetail(string='last commit with this repo already exists.', code='unique')]}
        commit, created = LastCommit.objects.update_or_create(
            repo=repo,
            commit_id=latest_commit["sha"],
            defaults={
                "author": latest_commit["commit"]["author"]["name"],
                "message": latest_commit["commit"]["message"],
                "timestamp": latest_commit["commit"]["author"]["date"],
            }
        )
        if not created:
            print(f"Commit {latest_commit['sha']} updated.")
        else:
            print(f"New commit {latest_commit['sha']} created.")


def get_github_access_token(github_user_id):
    try:
        token = GitHubToken.objects.get(github_id=github_user_id)

        if not is_token_valid(token.access_token):
            return token.refresh_access_token()
        return token.access_token
    except GitHubToken.DoesNotExist:
        raise Exception(f"No token found for GitHub user ID: {github_user_id}")


def is_token_valid(access_token):
    url = "https://api.github.com/user"
    headers = {"Authorization": f"token {access_token}"}
    response = requests.get(url, headers=headers)
    return response.status_code == 200


def get_all_md_file_paths(repo):

    markdown_files = []
    # Function to recursively get markdown files
    def get_files_in_directory(directory):
        contents = repo.get_contents(directory)
        for content_file in contents:
            a = content_file.name.endswith(".md")
            b = is_file_translated(content_file.name)

            logger.info(f"content_file:{content_file.type}, {content_file.name}, Is md? {a}, Is translated? {b}")

            if content_file.type == "dir":
                get_files_in_directory(content_file.path)
            elif not is_file_translated(
                content_file.name
            ):
                markdown_files.append(content_file.path)

    get_files_in_directory("")
    return markdown_files


def get_and_store_repo_data(access_token, github_user_id, repo_name):
    headers = {"Authorization": f"token {access_token}"}
    repo_url = f"https://api.github.com/repos/{github_user_id}/{repo_name}"
    response = requests.get(repo_url, headers=headers)

    if response.status_code == 200:
        repo_data = response.json()
        repository_data = {"user_id": github_user_id, "repo_name": repo_data["name"]}
        serializer = RepositorySerializer(data=repository_data)
        if serializer.is_valid():
            serializer.save()
        else:
            print(f"Error saving repository {repo_name}: {serializer.errors}")
    else:
        print(f"Failed to fetch repository {repo_name}: {response.status_code}")

    return True


# def store_markdown_file(access_token, github_user_id, repo_name):
#     markdown_files = get_markdown_files(access_token, github_user_id, repo_name)

#     repository, created = Repository.objects.get_or_create(
#         user_id=github_user_id, 
#         repo_name=repo_name,
#         account_type=github_account_type
#     )

#     for file_name, file_info in markdown_files.items():
#         markdown_file_data = {
#             "repo": repository.id,
#             "file_name": file_name,
#             "file_path": file_info["file_path"],
#             "status": file_info["status"],
#         }

#         serializer = MarkdownFileSerializer(data=markdown_file_data)
#         if serializer.is_valid():
#             serializer.save()
#         else:
#             print(f"Error saving markdown file {file_name}: {serializer.errors}")

#     return True


def get_repository_data(access_token, github_user_id, repo_name):
    repo_url = f"https://api.github.com/repos/{github_user_id}/{repo_name}"
    headers = {"Authorization": f"token {access_token}", "Accept": "application/json"}
    response = requests.get(repo_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return None


def get_markdown_file(github_user_id, access_token, repo_name, file_path):
    url = f"https://api.github.com/repos/{github_user_id}/{repo_name}/contents/{file_path}"

    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        file_content = response.json()
        # File content is base64 encoded, so decode it
        file_data = base64.b64decode(file_content["content"]).decode("utf-8")
        return file_data
    else:
        # Handle errors
        print(f"Error: {response.status_code} - {response.json().get('message')}")
        return None


def reset_github_branch(github_token, github_user_id, repo_name, branch_name):
    """
    resetting coop branch to keep up with main branch
    """
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    try:
        # Get the latest commit SHA from the main branch
        main_branch_url = f"https://api.github.com/repos/{github_user_id}/{repo_name}/git/refs/heads/main"
        sha = requests.get(main_branch_url, headers=headers).json()["object"]["sha"]

        # Delete the branch if it exists
        branch_url = f"https://api.github.com/repos/{github_user_id}/{repo_name}/git/refs/heads/{branch_name}"
        requests.delete(branch_url, headers=headers)

        # Create a new branch
        new_branch_url = (
            f"https://api.github.com/repos/{github_user_id}/{repo_name}/git/refs"
        )
        payload = {"ref": f"refs/heads/{branch_name}", "sha": sha}
        new_branch_info = requests.post(
            new_branch_url, headers=headers, json=payload
        ).json()

        return new_branch_info

    except requests.RequestException as e:
        raise str(e)


def is_file_translated(file_name):

    pattern = r"^[A-Za-z0-9]+\.[a-z]+\.[a-z]+$"

    return bool(re.match(pattern, file_name))


def get_commit_diff(
    access_token, repo_name, github_user_id, commit_hash1, commit_hash2
):
    """
    get difference between two commit

    return a list of file name (including path) that has been changed
    """
    url = f"https://api.github.com/repos/{github_user_id}/{repo_name}/compare/{commit_hash1}...{commit_hash2}"
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception("Failed to fetch data from GitHub")

    files_data = response.json()
    files_data = files_data.get("files", [])

    changed_files = []
    for change in files_data:
        changed_files.append(change["filename"])
    return changed_files


def get_translate_tasks(changed_files, repo):
    """
    return a list contain tasks needs to be performed
    {
            'file_type': 'readme',
            'file_path': 'file_path'
    }
    """
    tasks = []
    docs_dir = get_docs_path_from_config(repo)

    for file_path in changed_files:
        file_name = os.path.basename(file_path)
        if is_file_translated(file_name):
            pass

        task = {"file_type": "", "file_path": file_path}

        if file_name == "README.md" and not file_path.startswith(docs_dir):
            task["file_type"] = "readme"
        elif file_name.endswith(".md") and file_path.startswith(docs_dir):
            task["file_type"] = "docs"
        elif file_name.lower().endswith(settings.SUPPORTED_IMAGE_EXTENSIONS):
            if file_path.startswith(docs_dir):
                task["file_type"] = "docs_image"
            else:
                task["file_type"] = "readme_image"
        else:
            pass

        tasks.append(task)
    
    return tasks


def translate_readme(repo, file_path, languages, languages_codes, branch_name="co-op-translator"):
    """
    """
    docs_dir = get_docs_path_from_config(repo)
    
    # Extract the markdown file content
    readme_file = repo.get_contents(file_path, ref=branch_name)
    readme_content = readme_file.decoded_content.decode()
    
    print(f"Translating {file_path}... ")

    # Loop through each language and create translated files
    for language, code in zip(languages, languages_codes):
        translated_content = translate_string(readme_content, language, code, docs_dir, file_path)

        # Define the translations folder and file path
        translations_dir = os.path.join(os.path.dirname(file_path), "translations")
        translated_file_path = os.path.join(translations_dir, f"README.{code}.md")

        # Ensure the translations directory exists in the repository
        try:
            repo.get_contents(translations_dir, ref=branch_name)
        except:
            repo.create_file(
                os.path.join(translations_dir, ".gitkeep"),
                "Create translations directory",
                "",
                branch=branch_name,
            )

        try:
            existing_file = repo.get_contents(translated_file_path, ref=branch_name)
            repo.update_file(
                existing_file.path,
                f"Update translated {file_path} in {language}",
                translated_content,
                existing_file.sha,
                branch=branch_name,
            )
        except GithubException:
            repo.create_file(
                translated_file_path,
                f"Add translated {file_path} in {language}",
                translated_content,
                branch=branch_name,
            )


def translate_doc(repo, file_path, languages, language_codes, branch_name="co-op-translator"):
    """
    Translates a documentation file and stores the translated versions in
    language-specific subfolders under /docs.
    
    Args:
        repo: The repository object.
        file_path: Path to the original documentation file.
        languages: List of languages to translate the file into.
        branch_name: The branch where changes will be committed.
    """
    # Extract the markdown file content
    docs_dir = get_docs_path_from_config(repo)
    logger.info(f"docs_dir is {docs_dir}")

    try:
        doc_file = repo.get_contents(docs_dir, ref=branch_name)
    except Exception as e:
        print(f"{e}: Failed to get contents of docs_dir, retrying...")
    else:
        raise Exception(f"The docs folder {docs_dir} does not exist in the repository.")

    # Extract the markdown file content
    doc_file = repo.get_contents(file_path, ref=branch_name)
    doc_content = doc_file.decoded_content.decode()

    # Loop through each language and create translated files
    for language, code in zip(languages, language_codes):
        logger.info(f"Translating {file_path} into {language} ({code})")
        translated_content = translate_string(doc_content, language,code,docs_dir, file_path)

        # Define the translations folder and file path
        docs_subpath = os.path.relpath(file_path, docs_dir)
        logger.info(f"docs_subpath: {docs_subpath}")
        language_dir = os.path.join(docs_dir, 'translations', code)
        logger.info(f"language_dir: {language_dir}")
        translated_file_path = os.path.join(language_dir, docs_subpath)
        logger.info(f"translated_file_path: {translated_file_path}")

        # Ensure the translations directory exists in the repository
        translations_dir = os.path.dirname(translated_file_path)
        logger.info(f"translations_dir: {translations_dir}")
        try:
            logger.info(f"Getting contents of {translations_dir} (check for .gitkeep)")
            gitkeep_dir = repo.get_contents(os.path.join(translations_dir, ".gitkeep"), ref=branch_name)
            # _ = repo.get_contents(translations_dir, ref=branch_name)
            break
        # except GithubException:
        #     print(f"Failed to get contents of translations_dir, retrying {i}...")
        #     time.sleep(1)
        # else:
        except Exception as e:
            logger.warning(f"{e}: Failed find a dir with .gitkeep on {translated_file_path}, so creating new dir with .gitkeep")
            try:
                repo.create_file(
                os.path.join(translations_dir, ".gitkeep"),
                "Create translations directory",
                "",
                branch=branch_name,
                )
            except GithubException as e:
                # check if code 422
                if e.status == 422:
                    print(f"Failed to create .gitkeep on {translations_dir}")

                
                


        # Append language code to the file name
        translated_file_path = os.path.splitext(translated_file_path)
        translated_file_path = f"{translated_file_path[0]}.{code}{translated_file_path[1]}"
        logger.info(f"new translated_file_path: {translated_file_path}")

        # Check if the translated file already exists and update or create accordingly
        try:
            logger.info(f"Getting contents of {translated_file_path}")
            existing_file = repo.get_contents(translated_file_path, ref=branch_name)
            repo.update_file(
                existing_file.path,
                f"Update translated {file_path} in {language}",
                translated_content,
                existing_file.sha,
                branch=branch_name,
            )

        except Exception as e:
            print(f"{e}: Failed to update translated file on {translated_file_path}, so creating a new one")
            repo.create_file(
                translated_file_path,
                f"Add translated {file_path} in {language}",
                translated_content,
                branch=branch_name,
            )



def translate_image(repo, image_type, file_path, languages, language_codes, fontnames, branch_name="co-op-translator"):
    """
    Translates the description of an image file and updates or creates translation files in the repository.
    """
    is_readme = image_type == "readme_image"
    logger.info(f"Translating {image_type}: {file_path}. ")
    # Get the file from GitHub
    file = repo.get_contents(file_path, ref=branch_name)
    
    if file.content == '':
        # warnings.warn(f"File {file_path} is empty or too large")
        file_content = get_github_image_content(
            settings.ROBOT_PAT,
            repo.full_name,
            file_path, 
        )
        
    else:
        file_content = base64.b64decode(file.content)

    # Ensure the translated_images folder exists
    
    # if readme image, store in translated_images folder on the same level
    if is_readme:
        translated_folder = os.path.join(os.path.dirname(file_path), "translations", "translated_images")
    else: # else it's a doc image, store in docs/translated_images folder
        translated_folder = os.path.join(get_docs_path_from_config(repo), "translated_images")
        
        
        
    try:
        repo.get_contents(translated_folder, ref=branch_name)
        logger.info(f"The folder '{translated_folder}' already exists.")
    except:
        repo.create_file(f"{translated_folder}/.gitkeep", "Create translated_images folder", "", branch=branch_name)
        logger.info(f"The folder '{translated_folder}' has been created.")

    original_filename = os.path.basename(file_path).split('.')[0]
    original_extension = os.path.splitext(file_path)[1]  
    
    
    # Translate and save the image for each language

    for language, code, fontname in zip(languages, language_codes, fontnames):
        translated_content = translate_image_content(file_content, language, fontname)
        if not translated_content:
            break
        

        logger.info("Generating New Image Hash Name")
        hash = get_unique_id(file_path)
        new_filename = f"{original_filename}.{hash}.{code}{original_extension}"
        translated_file_path = os.path.join(translated_folder, new_filename)
        
        try:
            existing_file = repo.get_contents(translated_file_path, ref=branch_name)
            repo.update_file(
                existing_file.path,
                f"Update translated {file_path} in {language}",
                translated_content,
                existing_file.sha,
                branch=branch_name,
            )
        except GithubException:
            repo.create_file(
                translated_file_path,
                f"Add translated {file_path} in {language}",
                translated_content,
                branch=branch_name,
            )



def translate_and_update_files(diff_files, repo, languages, languages_codes, fontnames):
    translate_tasks = get_translate_tasks(diff_files, repo)
    logger.info(f"translation tasks: {translate_tasks}")

    for task in translate_tasks:
        if task["file_type"] == "readme":
            translate_readme(repo, task["file_path"], languages, languages_codes)
        elif task["file_type"] == "docs":
            translate_doc(repo, task["file_path"], languages, languages_codes)
        elif task["file_type"] == "docs_image" or task["file_type"] == "readme_image":
            translate_image(repo, task["file_type"], task["file_path"], languages, languages_codes,fontnames)
        else:
            pass

def merge_branches(repo, base_branch, head_branch):
    try:
        repo.merge(base=base_branch, head=head_branch)
        print(f"Successfully merged {head_branch} into {base_branch}")
    except Exception as e:
        raise Exception(e)

# -------------------------------------#
#       invite related functions       #
# -------------------------------------#

def send_invitation(
        access_token, 
        repo_full_name,
        invitee_github_id
    ):
    

    try:
        # Get the repository
        g = Github(access_token)
        repo = g.get_repo(f"{repo_full_name}")
        print(f"Sending join request by robot to {repo_full_name}")
        repo.add_to_collaborators(invitee_github_id, permission="push")
        logger.info(f"Join request sent by robot to {repo_full_name}")
    except Exception as e:
        raise Exception(f"Failed to send join request by robot to {repo_full_name}: {str(e)}")

def accept_invitations(access_token):
    """
    Accept all invitations to join repos.
    
    - Should be used on a robot account.
    """
    g = Github(access_token)
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # List pending invitations using PyGithub
    user = g.get_user()
    invitations = user.get_invitations()
    
    for invitation in invitations:
        invitation_id = invitation.id
        try:
            # Accept each invitation using requests
            accept_response = requests.patch(f"https://api.github.com/user/repository_invitations/{invitation_id}", headers=headers)
            if accept_response.status_code != 204:
                raise Exception(f"Failed to accept invitation {invitation_id}: {accept_response.json()}")
        except Exception as e:
            raise Exception(f"Failed to accept invitation {invitation_id}: {str(e)}")


def get_unique_id(file_path):
    
    # Convert the file path to bytes
    file_path_bytes = file_path.encode('utf-8')
    
    # Create a SHA-256 hash object
    hash_object = hashlib.sha256()
    
    # Update the hash object with the bytes of the file path
    hash_object.update(file_path_bytes)
    
    # Generate the hexadecimal digest
    unique_identifier = hash_object.hexdigest()
    logger.info(f"HASH in GET UNIQUE ID for: {file_path} HASH={unique_identifier}")
    return unique_identifier

def get_github_image_content(repo_owner, repo_name, file_path, ref="main"):
    try:
        # Construct the raw GitHub content URL
        raw_url = f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{ref}/{file_path}"
        
        # Send a GET request to fetch the image content
        response = requests.get(raw_url)
        response.raise_for_status()  # Raise an error for unsuccessful requests
        
        # Check if the response is an image (assuming it's PNG based on your requirement)
        if response.headers.get('content-type') == 'image/png':
            return response.content  # Return image content in bytes
        else:
            raise ValueError(f"File at {raw_url} is not a PNG image.")
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching GitHub content: {e}")
        return None
    except ValueError as ve:
        print(ve)
        return None
    

def get_github_image_content(access_token, repo_full_name, file_path, ref="co-op-translator"):
    try:
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github.v3.raw"  # Ensure raw content is returned
        }
        
        raw_url = f"https://raw.githubusercontent.com/{repo_full_name}/{ref}/{file_path}"

        response = requests.get(raw_url, headers=headers)
        response.raise_for_status()  # Raise an error for unsuccessful requests
        
        # Check if the response is an image (assuming it's PNG based on your requirement)
        return response.content  # Return image content in bytes
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching GitHub content: {e}")
        return None
    except ValueError as ve:
        print(ve)
        return None
