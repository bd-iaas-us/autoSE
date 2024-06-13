![](https://github.com/bd-iaas-us/autoSE/actions/workflows/ci.yml/badge.svg)

# AutoSE

AutoSE is an AI-agent-based service that automates software development activities. It aims to automatically solve some complex software engineering tasks.

# Features

* Lint:
  * Scan a code file or a git diff to identify potential code problems.
  * Offer suggestions and potential fixes for the problems. 
* Dev:
  * Given a github task or a local task description file, generate a local git patch for the specifiled task. 


## Installation

1. Install the binary:

```
curl -fsSL https://raw.githubusercontent.com/bd-iaas-us/autoSE/main/install.sh | bash
```

2. Setup the environment variables `API_URL` and `API_KEY`.

AutoSE is not only a commandline tool. It relies on a backend with the power of LLM, RAG and vector storage. You can setup your own backend or use an existing backend. We will update the document soon on how to setup your own backend. Before that, just find an existing backend and set environment variables `API_URL` and `API_KEY` to point to it.



# How To Use

## lint

### diff mode

Just run `autose --diff-mode lint <fileName>` to find the potential problems in your code and see the recommended fixes.


### single file mode

`autose --diff-mode lint <fileName>`

### project mode

If the command `autose --diff-mode` is executed in a git-managed directory, autoSE calls git diff to check for any potential issues in the diffs.

Here is an example screenshot:

![lint_usage](./docs/images/lint_usage.png)

## dev


![lint_usage](./docs/images/dev_usage.png)

## Run AutoSE Server
1. Install Dependencies:
Navigate to the root of the repository.

`pip install -r server/april/requirements.txt`

2. Clone the SWE-agent Repository 

`git clone https://github.com/bd-iaas-us/SWE-agent.git`

3. Create a `keys.cfg` File at the Root of the SWE-agent Repository

`OPENAI_API_KEY: 'OpenAI API Key Here if using OpenAI Model'`

4. Navigate to the Root of the SWE-agent Repository and Start the Uvicorn Server

`uvicorn --port 8000 --app-dir {your_path} api:app`

Replace {your_path} with the actual path to your application directory, for example `uvicorn --port 8000 --app-dir /root/project/autoSE/server/april api:app`.

5. Send a Sample cURL Request Request

`curl --location 'http://127.0.0.1:8000/dev' \
--header 'Authorization: xxxxxx' \
--header 'Content-Type: application/json' \
--data '{
  "repo": "https://github.com/bd-iaas-us/autoSE",
  "prompt": "add README.md",
  "model": "openai:gpt4"
}'`
# Architecture

![architecture](./docs/images/architecture.png)
