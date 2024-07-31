#!/usr/bin/env bash
set -eo pipefail

echo "format python code..."
yapf --in-place --recursive .
ruff check --fix
echo "format rust code..."
cd client/april && cargo fmt

