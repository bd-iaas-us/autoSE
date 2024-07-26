import os

from datetime import datetime
import tempfile
WORK_SPACE = tempfile.gettempdir() + "/cover/workspace"

import git

# The function generate a suffix based upon the datetime it is called
def gen_folder_suffix():
    return datetime.now().strftime("%m-%d-%Y_%H-%M-%S")

# The function get the path where the repository is cloned
# the path is created if not exists
def get_repo_folder(owner: str, repo: str, suffix=""):
    # Specify the path where you want to create the folder
    folder_path = WORK_SPACE + f'/{owner}/{repo}'
    if len(suffix) > 0:
        folder_path = folder_path + "_" + suffix

    if not os.path.exists(folder_path):
        # Create the folder
        os.makedirs(folder_path, exist_ok=True)
        return False, folder_path
    return True, folder_path

# The function get the path where the data is saved
# the path is created if not exists
def get_data_folder(owner: str, repo: str, suffix=""):
    # Specify the path where you want to create the folder
    folder_path = WORK_SPACE + f'/{owner}/{repo}_data'
    if len(suffix) > 0:
        folder_path = folder_path + "_" + suffix

    if not os.path.exists(folder_path):
        # Create the folder
        os.makedirs(folder_path, exist_ok=True)
        return False, folder_path
    return True, folder_path

# The function retrieve the owner and repository parts from url object
def get_owner_repo(url_obj):
    path = url_obj.path
    tokens = path.split("/")
    i = 0
    if len(tokens[i]) == 0:
        i += 1
    return tokens[i], tokens[i+1]

def clone_repo(url_obj, token = None, folder_suffix =""):
    owner, repo = get_owner_repo(url_obj)
    repo_exist, repo_folder = get_repo_folder(owner, repo, folder_suffix)
    if not repo_exist:
        url = f'{url_obj.scheme}://'
        if token is not None and len(token) > 0:
           url += f'oauth2:{token}@'
        url += f'{url_obj.hostname}/{owner}/{repo}'
        git.Git().clone(url, repo_folder)
        return True, repo_folder
    return False, repo_folder