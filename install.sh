#!/bin/bash

# Define the GitHub repository and the name of the binary.
GITHUB_REPO="bd-iaas-us/AILint"
BINARY_NAME="ailint"

# Check the operating system
OS="$(uname)"

# If the operating system is Linux, set the target directory to '/usr/local/bin'
# If the operating system is Darwin (macOS), set the target directory to '${HOME}/.local/bin'
if [[ "$OS" == "Linux" ]]; then
  TARGET_DIR="/usr/local/bin"
elif [[ "$OS" == "Darwin" ]]; then
  TARGET_DIR="${HOME}/.local/bin"
else
  echo "Unsupported operating system: $OS"
  exit 1
fi

command -v unzip >/dev/null ||
    error 'unzip is required to install ailint'

# Make sure the target dir exists
mkdir -p "${TARGET_DIR}"

TARGET_FILE="${TARGET_DIR}/${BINARY_NAME}"

case $(uname -ms) in
'Darwin x86_64')
    target=x86_64-apple-darwin
    ;;
'Darwin arm64')
    target=aarch64-apple-darwin
    ;;
'Linux x86_64' | *)
    target=x86_64-unknown-linux-musl
    ;;
esac

# Set up temporary directory for download and extraction
TMPDIR=$(mktemp -d)

GITHUB=${GITHUB-"https://github.com"}

github_repo="$GITHUB/$GITHUB_REPO"

if [[ $# = 0 ]]; then
    AILINT_BINARY_URL=$github_repo/releases/latest/download/ailint-$target.tar.gz
else
    AILINT_BINARY_URL=$github_repo/releases/download/$1/ailint-$target.tar.gz
fi

# Check if the download URL was found.
if [ -z "${AILINT_BINARY_URL}" ]; then
    echo "Failed to find the download URL for the '${BINARY_NAME}' binary."
    echo "Please check the GitHub repository and release information."
    exit 1
fi

# Download the 'ailint' CLI binary from the specified URL.
echo "Downloading '${BINARY_NAME}' CLI binary..."
curl -L -o "${TMPDIR}/${BINARY_NAME}.tar.gz" "${AILINT_BINARY_URL}"

# Extract the zip file in the temporary directory.
# echo "tar zxvf \"${TMPDIR}/${BINARY_NAME}.tar.gz\" -C \"${TMPDIR}\""
tar zxvf "${TMPDIR}/${BINARY_NAME}.tar.gz" -C "${TMPDIR}" ||
    error 'Failed to extract ailint'

# Move the binary to the target directory.
mv "${TMPDIR}/ailint" "${TARGET_DIR}/${BINARY_NAME}"

# Make the downloaded binary executable.
chmod +x "${TARGET_FILE}"

# Clean up the temporary directory.
# rm -rf "${TMPDIR}"

if [ -f "${TARGET_FILE}" ]; then
    echo "Successfully installed '${BINARY_NAME}' CLI."
    echo "The binary is located at '${TARGET_FILE}'."

    # Provide instructions for adding the target directory to the PATH.
    echo -e "\033[0;32m"
    echo -e "To use the '${BINARY_NAME}' command, add '${TARGET_DIR}' to your PATH."
    echo -e "You can do this by running one of the following commands, depending on your shell:"
    echo -e "\033[0m"
    echo -e "\033[0;32mFor bash:"
    echo -e "\033[1m  echo 'export PATH=\"${TARGET_DIR}:\$PATH\"' >> ~/.bashrc && source ~/.bashrc\033[0m"
    echo -e "\033[0;32m"
    echo -e "\033[0;32mFor zsh:"
    echo -e "\033[1m  echo 'export PATH=\"${TARGET_DIR}:\$PATH\"' >> ~/.zshrc && source ~/.zshrc\033[0m"
    echo -e "\033[0;32m"
    echo -e "After running the appropriate command, you can use '${BINARY_NAME}'.\033[0m"


else
    echo "Installation failed. '${BINARY_NAME}' CLI could not be installed."
fi