import json
import os
import subprocess
from typing import Optional,List


from logger import init_logger
from openai import OpenAI
from pydantic import BaseModel

logger = init_logger(__name__)


class Resource(BaseModel):
    resource_type: str
    description: str


class ResourceTypes(BaseModel):
    resources: list[Resource]


client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

git_repo = '/root/git/terraform-provider-volcengine/'
doc_path = f'{git_repo}/website/docs/r'

tf_validate_dir = '/data00/jxp/tf'
tf_validate_file = 'test.tf'

def check_git_repo_exist():
    if not os.path.isdir(git_repo):
        raise Exception("clone git repo terraform-provider-volcengine first...")
    if not os.path.isdir(f'{git_repo}/.git/'):
        raise Exception(f"{git_repo} does not have .git")
#check git repo
check_git_repo_exist()




def build_system_1(doc_path):
    system_1 = "你是一个火山引擎的资源分类器，以下是对不同资源的描述。\n"
    for f in os.listdir(doc_path):
        with open(os.path.join(doc_path, f)) as resource_doc:
            lines = resource_doc.readlines()
            for idx, line in enumerate(lines):
                if line.startswith('page_title:'):
                    system_1 += line.split(':')[2].strip()[0:-1] + ': '
                if line.startswith('description:'):
                    system_1 += lines[idx + 1].strip() + ';\n'
                    break
    return system_1


def tf_validate(tf_code):
    tf_validate_file_path = os.path.join(tf_validate_dir, tf_validate_file)
    with open(tf_validate_file_path, 'w') as f:
        f.write(tf_code + '\n')

    cmd = f'cd {tf_validate_dir}; tf validate'
    ret, output = subprocess.getstatusoutput(cmd)
    logger.info(f'validate result: {output}')
    return ret, output



def git_shell(*args):
    result = subprocess.run(
            list(args),
            cwd=git_repo,
            check=True, 
            text=True,
            capture_output=True
    )
    print(result)


def fetch_commit(git_commit_hash: Optional[str]=None):
    try:
        git_shell('git', 'fetch')
        if git_commit_hash is None:
            git_shell('git', 'reset', '--hard', 'origin/master')
        else:
            git_shell('git', 'checkout', git_commit_hash)
    except:
        if git_commit_hash is not None:
            raise Exception(f"try to checkout commit #{git_commit_hash} failed")
        else:
            raise Exception('failed to clone document repo')


def handle_tf(input: str, git_commit_hash: Optional[str] = None) -> str:
    if git_commit_hash is not None and git_commit_hash == "":
        raise Exception("git_commit_hash can not be ''")

    user_1 = f"用户问了'{input}'，请告诉我需要哪种资源类型的文档，用json表示。"
    logger.info(user_1)

    fetch_commit(git_commit_hash)

    system_1 = build_system_1(doc_path)
    response = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        response_format=ResourceTypes,
        messages=[{
            "role": "system",
            "content": system_1
        }, {
            "role": "user",
            "content": user_1
        }])
    resp1 = response.choices[0].message.content
    resp1_json = json.loads(resp1)
    logger.info(resp1_json)

    system_2 = "你是一个火山引擎的infrastructure as code助手，并且可以产生terraform代码。针对不同资源类型，有以下文档。\n"
    for resource in resp1_json['resources']:
        # todo: use function call
        if 'type' in resource:
            resource_file = '_'.join(
                resource['type'].split('_')[1:]) + '.html.markdown'
        if 'resource_type' in resource:
            resource_file = '_'.join(
                resource['resource_type'].split('_')[1:]) + '.html.markdown'
        with open(os.path.join(doc_path, resource_file)) as resource_doc:
            system_2 += resource_doc.read() + "\n"

    user_2 = f'用户问了"{input}"，请给出相应的terraform代码。如果required fields没提供，必须用""或[""]代替。如果field是optional的，那么不需要提供。如果是引用到的资源，也不需要提供。'

    messages = [{
        "role": "system",
        "content": system_2
    }, {
        "role": "user",
        "content": user_2
    }]

    while len(messages) < 7:
        response = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18", messages=messages)
        resp2 = response.choices[0].message.content
        # logger.info(resp2)
        start = '```hcl'
        end = '```'
        hcl_code_str = resp2[resp2.find(start) +
                             len(start):resp2.rfind(end)].strip()
        logger.info(hcl_code_str)

        ret, output = tf_validate(hcl_code_str)
        if not ret:
            return hcl_code_str
        else:
            logger.info("validate failed, try again.")
            messages.append({"role": "assistant", "content": resp2})
            messages.append({"role": "user", "content": output})

if __name__ == "__main__":
	handle_tf("test")
