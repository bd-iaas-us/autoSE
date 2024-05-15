![](https://github.com/bd-iaas-us/AILint/actions/workflows/ci.yml/badge.svg)
# AILint
AILint is a LLM-backed developer helper. it could privide code lint and wrote a patch for simple tasks.

# features

* It scans a file or a git diff to identify potential code problems, and offer suggestions. 
* It could accept task from a description file and try to write a patch for specifiled repository. 


## Installation

1. Install the binary:

```
curl -fsSL https://raw.githubusercontent.com/bd-iaas-us/AILint/main/install.sh | bash
```

2. Setup the environment variables `API_URL` and `API_KEY`.

AILint is not only a commandline tool. It relies on a backend with the power of LLM, RAG and vector storage. You can setup your own backend or use an existing backend. We will update the document soon on how to setup your own backend. Before that, just find an existing backend and set environment variables `API_URL` and `API_KEY` to point to it.



# How To Use

## lint

### diff mode

Just run `ailint --diff-mode lint <fileName>` to find the potential problems in your code and see the recommended fixes.


### single file mode
`ailint --diff-mode lint <fileName>`

### project mdoe

If the command `ailint --diff-mode` is executed in a git-managed directory, ailint calls git diff to check for any potential issues in the diffs.

Here is an example screenshot:

![lint_usage](./docs/images/lint_usage.png)

## dev


![lint_usage](./docs/images/dev_usage.png)


# Architecture

![architecture](./docs/images/architecture.png)
