
import os
import sys
import requests
import json
import re
from git import Repo
from fastapi.responses import JSONResponse, Response, StreamingResponse
from urllib.parse import urlparse
from github import Github
from task import Task, TaskStatus

from logger import init_logger
logger = init_logger(__name__)

# All the project related files, include repository, files generated by agent
# are saved in a folder generated by owner&repo under WORK_SPACE
WORK_SPACE = os.path.expanduser("~") + "/.ailint/workspace"

# Dict for all the tasks 
tasks = {}

# Hard coded personal token, TODO: Replace it with an official one!!!
github_token = os.environ.get('GITHUB_TOKEN')

class Agent:
    def __init__(self, args: dict):
        self.args = args
        self.task_id = args["task_id"]

    def call(self, arguments):
        pass

class SWEAgent(Agent):
    def __init__(self, args: dict):
        super().__init__(args)

    def call(self):
        data_path = self.args["data_path"]
        repo_path = self.args["repo_path"]
        return JSONResponse(status_code=200, content={'message': "SWEAgent not connected yet", "task_id": self.task_id})

# The function get the path where the repository is cloned
# the path is created if not exists
def getRepoFolder(owner: str, repo: str)->tuple[bool, str]:
    # Specify the path where you want to create the folder
    folderPath = WORK_SPACE + f'/{owner}/{repo}'
    if not os.path.exists(folderPath):
        # Create the folder
        os.makedirs(folderPath, exist_ok=True)
        return [False, folderPath]
    return [True, folderPath]

# The function get the path where the data is saved
# the path is created if not exists
def getDataFolder(owner: str, repo: str) -> tuple[bool, str]:
    # Specify the path where you want to create the folder
    folderPath = WORK_SPACE + f'/{owner}/{repo}_data'
    if not os.path.exists(folderPath):
        # Create the folder
        os.makedirs(folderPath, exist_ok=True)
        return [False, folderPath]
    return [True, folderPath]

# The function retrieve the owner and repository parts from url object
def getOwnerAndRepo(urlObj)->tuple[str, str]:
    path = urlObj.path
    tokens = path.split("/")
    i = 0
    if len(tokens[i]) == 0:
        i += 1
    return [tokens[i], tokens[i+1]]


# The function generate the github API url, like
#   https://api.github.com/repos/{owner}/{repo}
#  NOTE: The function is not used for now, but keep it
#  in case we call github api in the future
def generateGithubApiUrl(urlObj):
    gitHubApi = urlObj.hostname
    # If the host name starts with "www.", trim it
    if gitHubApi.startswith("www."):
       gitHubApi = gitHubApi[4:]
    # Assemble the github api url
    gitHubApi = "api." + gitHubApi[4:]
    owner, repo = getOwnerAndRepo(urlObj)
    return f'{urlObj.scheme}://{gitHubApi}/repos/{owner}/{repo}/'

# Parses the promptObj and return the url object
def parsePromptObj(promptObj: dict):
    repoUrl = promptObj["repo"]
    if repoUrl is not None:
        urlObj = urlparse(repoUrl)
        return urlObj
    return None


def getTask(taskId):
    if taskId in tasks:
        return tasks[taskId]
    return None

# The handler function for getting status
def handle_status(taskId):
    logger.info(f'getting status for taskId: {taskId}')

    task = getTask(taskId)
    if task is None:
        message = f'The task {taskId} does not exist'
        return JSONResponse(status_code=404, content={'message': message})
    return JSONResponse(status_code=200, content={'status': task.get_status().name})


# The handler function for github issue
def handle_prompt(promptObj: dict):
    """
    The worker function to handle a dev request for a  project based
    prompt
    The promptObj contains "repo", "token" and "prompt"
    """
    logger.info(f'processing prompt: {promptObj["prompt"]}')

    if "repo" not in promptObj:
        return JSONResponse(status_code=400, content={'message': "The repo missed in request"})

    urlObj = parsePromptObj(promptObj)
    if urlObj is None or urlObj.path is None:
        return JSONResponse(status_code=400, content={'message': "The repo specified is invalid"})

    newTask = Task(promptObj["prompt"])
    tasks[newTask.id] = newTask

    # Clone the project to local
    owner, repo = getOwnerAndRepo(urlObj)
    repoExist, repoFolder = getRepoFolder(owner, repo)
    _, dataFolder = getDataFolder(owner, repo)

    # TODO: Add support to update the repo
    if not repoExist:
        Repo.clone_from(promptObj["repo"], repoFolder)

    newTask.set_status(TaskStatus.RUNNING)
    # Call agent to query
    agent = SWEAgent({"task_id": newTask.id, "data_path": dataFolder, "repo_path": repoFolder})
    agentResp = agent.call()

    return agentResp
