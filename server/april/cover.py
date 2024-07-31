import argparse
import os
import time
from datetime import datetime, timedelta
from threading import Lock, Thread
from typing import Dict
from urllib.parse import urlparse

import utils
from cover_agent.CoverAgent import CoverAgent
from cover_agent.version import __version__
from fastapi import HTTPException
from logger import init_logger
from task import Task, TaskStatus

logger = init_logger(__name__)

tasks_mutex = Lock()
tasks: Dict[str, Task] = {}


def get_task(taskId):
    with tasks_mutex:
        if taskId in tasks:
            return tasks[taskId]
    return None


def add_task(task: Task):
    with tasks_mutex:
        # task id is a UUID, dup not checked here
        tasks[task.id] = task


class Agent:

    def __init__(self, repo_path, source_file_path, test_file_path, task):
        self.repo_path = repo_path
        self.source_file_path = source_file_path
        self.test_file_path = test_file_path
        self.task = task

    def run(self):
        test_dir = os.path.dirname(self.test_file_path)

        # sys.argv.extend(['--source-file-path', self.source_file_path, '--test-file-path', self.test_file_path])
        # sys.argv.extend(['--code-coverage-report-path', os.path.join(test_dir, 'coverage.xml'), '--test-command', '/usr/local/go/bin/go test -coverprofile=coverage.out && /root/go/bin/gocov convert coverage.out | /root/go/bin/gocov-xml > coverage.xml', '--test-command-dir', test_dir,])
        # sys.argv.extend(['--coverage-type', 'cobertura', '--desired-coverage', '70', '--max-iterations', '1'])
        # logger.info(f'sys.argv: {sys.argv}')
        # main.main()

        parser = argparse.ArgumentParser(
            description=f"Cover Agent v{__version__}")
        parser.add_argument("--source-file-path",
                            required=True,
                            help="Path to the source file.")
        parser.add_argument("--test-file-path",
                            required=True,
                            help="Path to the input test file.")
        parser.add_argument(
            "--test-file-output-path",
            required=False,
            help="Path to the output test file.",
            default="",
            type=str,
        )
        parser.add_argument(
            "--code-coverage-report-path",
            required=True,
            help="Path to the code coverage report file.",
        )
        parser.add_argument(
            "--test-command",
            required=True,
            help="The command to run tests and generate coverage report.",
        )
        parser.add_argument(
            "--test-command-dir",
            default=os.getcwd(),
            help=
            "The directory to run the test command in. Default: %(default)s.",
        )
        parser.add_argument(
            "--included-files",
            default=None,
            nargs="*",
            help=
            'List of files to include in the coverage. For example, "--included-files library1.c library2.c." Default: %(default)s.',
        )
        parser.add_argument(
            "--coverage-type",
            default="cobertura",
            help="Type of coverage report. Default: %(default)s.",
        )
        parser.add_argument(
            "--report-filepath",
            default="test_results.html",
            help="Path to the output report file. Default: %(default)s.",
        )
        parser.add_argument(
            "--desired-coverage",
            type=int,
            default=90,
            help="The desired coverage percentage. Default: %(default)s.",
        )
        parser.add_argument(
            "--max-iterations",
            type=int,
            default=10,
            help="The maximum number of iterations. Default: %(default)s.",
        )
        parser.add_argument(
            "--additional-instructions",
            default="",
            help=
            "Any additional instructions you wish to append at the end of the prompt. Default: %(default)s.",
        )
        parser.add_argument(
            "--model",
            default="gpt-4o",
            help="Which LLM model to use. Default: %(default)s.",
        )
        parser.add_argument(
            "--api-base",
            default="http://localhost:11434",
            help=
            "The API url to use for Ollama or Hugging Face. Default: %(default)s.",
        )
        parser.add_argument(
            "--strict-coverage",
            action="store_true",
            help=
            "If set, Cover-Agent will return a non-zero exit code if the desired code coverage is not achieved. Default: False.",
        )

        args = parser.parse_args([
            '--source-file-path', self.source_file_path, '--test-file-path',
            self.test_file_path, '--code-coverage-report-path',
            os.path.join(test_dir, 'coverage.xml'), '--test-command',
            '/usr/local/go/bin/go test -coverprofile=coverage.out && /root/go/bin/gocov convert coverage.out | /root/go/bin/gocov-xml > coverage.xml',
            '--test-command-dir', test_dir, '--coverage-type', 'cobertura',
            '--desired-coverage', '50', '--max-iterations', '1'
        ])
        logger.info(args)

        agent = CoverAgent(args, self.task)
        Thread(target=agent.run).start()


def handle_cover(request) -> str:
    new_task = Task("cover task")
    logger.info(f'new_task: {new_task.get_id()}')
    add_task(new_task)
    try:
        url_obj = urlparse(request.repo)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"{e}")

    success, repo_folder = utils.clone_repo(url_obj, request.token,
                                            utils.gen_folder_suffix())
    if not success:
        #return JSONResponse(status_code=400, content={'message': "The repo specified exists or cannot be cloned"})
        raise HTTPException(
            status_code=400,
            detail="the repo specified exists or cannot be cloned")

    source_file_path = os.path.join(repo_folder, request.source_file)
    test_file_path = os.path.join(repo_folder, request.test_file)

    if not os.path.isfile(source_file_path):
        raise HTTPException(status_code=400,
                            detail="source file doesn't exist")

    if not os.path.isfile(test_file_path):
        raise HTTPException(status_code=400, detail="test file doesn't exist")

    new_task.set_status(TaskStatus.RUNNING)

    try:
        agent = Agent(repo_folder, source_file_path, test_file_path, new_task)
        agent.run()
        new_task.set_cover_repo_dir(repo_folder)
        new_task.set_cover_test_file(test_file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")
    return new_task.get_id()


def handle_cover_task(taskId) -> tuple[str, str]:
    logger.info(f'getting task info for taskId: {taskId}')

    task = get_task(taskId)
    if task is None:
        raise HTTPException(status_code=400,
                            detail=f"The task {taskId} does not exist")
    # get patch
    test_file = task.get_cover_test_file()
    logger.info(f'test_file: {test_file}')
    content = ""
    if test_file is not None:
        logger.info(f'reading test file: {test_file}')
        with open(test_file, 'r') as f:
            content = f.read()

    return (task.get_status().name, content)


def gen_cover_history_data(taskId: str):
    task = get_task(taskId)
    logger.info(f'get task: {task}')
    idx = 0
    last_update = datetime.now()
    logger.info(
        f'----------- start processing the history for task {task.get_id()} at {datetime.now()}'
    )
    while True:
        n = task.get_history_len()
        logger.info(f'history len: {n}')
        if n == idx:
            if datetime.now() - last_update > timedelta(minutes=1):
                logger.warn("client waits too long, quit...")
                return
            #TODO: use cond lock to replace time.sleep
            time.sleep(0.2)
            continue
        last_update = datetime.now()
        for i in range(idx, n):
            item = task.get_history(i)
            logger.info(item)
            yield str(item["content"])

            #swe-agent could run into error. in this case. should set status to ERROR
            if "submit" in item["action"]:
                task.set_status(TaskStatus.DONE)
                return
            if "exit" in item["action"]:
                task.set_status(TaskStatus.EXIT_COST)
                return
        idx = n
