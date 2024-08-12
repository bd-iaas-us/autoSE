import json
import os
import subprocess

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
doc_path = '/root/git/terraform-provider-volcengine/website/docs/r'

tf_validate_dir = '/data00/jxp/tf'
tf_validate_file = 'test.tf'

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


def tf_validate(tf_code):
    tf_validate_file_path = os.path.join(tf_validate_dir, tf_validate_file)
    with open(tf_validate_file_path, 'w') as f:
        f.write(tf_code + '\n')

    cmd = f'cd {tf_validate_dir}; tf validate'
    ret, output = subprocess.getstatusoutput(cmd)
    logger.info(f'validate result: {output}')
    return ret == 0


def handle_tf(input: str) -> str:
    user_1 = f"用户问了'{input}'，请告诉我需要哪种资源类型的文档，用json表示。"
    logger.info(user_1)

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

    user_2 = f'用户问了"{input}"，请给出相应的terraform代码。如果required fields没提供，必须用"<to_be_provided>"代替。如果field是optional的，那么不需要提供。如果是引用到的资源，也不需要提供。'

    response = client.chat.completions.create(model="gpt-4o-mini-2024-07-18",
                                              messages=[{
                                                  "role": "system",
                                                  "content": system_2
                                              }, {
                                                  "role": "user",
                                                  "content": user_2
                                              }])

    resp2 = response.choices[0].message.content
    # logger.info(resp2)
    start = '```hcl'
    end = '```'
    hcl_code_str = resp2[resp2.find(start) +
                         len(start):resp2.rfind(end)].strip()
    logger.info(hcl_code_str)

    if tf_validate(hcl_code_str):
        return hcl_code_str
    else:
        # todo: another loop
        logger.info('validate failed')
