#!/bin/bash
set -e

# Ensure script is run with bash
if [ -z "$BASH_VERSION" ]; then
    echo "Please run with bash"
    exit 1
fi

# Determine project root
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Python version check
REQUIRED_PYTHON_VERSION="3.11"
CURRENT_PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)

if [[ "$(printf '%s\n' "$REQUIRED_PYTHON_VERSION" "$CURRENT_PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_PYTHON_VERSION" ]]; then
    echo "Python version ${CURRENT_PYTHON_VERSION} is lower than required ${REQUIRED_PYTHON_VERSION}"
    exit 1
fi

# Create virtual environment
if [ ! -d "${PROJECT_ROOT}/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "${PROJECT_ROOT}/venv"
fi

# Activate virtual environment
source "${PROJECT_ROOT}/venv/bin/activate"

# Update pip and setuptools
pip install --upgrade pip setuptools wheel

# Install project dependencies
pip install -r "${PROJECT_ROOT}/requirements.txt"

# Install development dependencies
pip install pytest pylint mypy black

# Configure environment variables
if [ -f "${PROJECT_ROOT}/.env" ]; then
    export $(cat "${PROJECT_ROOT}/.env" | xargs)
fi

# Verify installation
python3 -c "import crewai; print('CrewAI installed successfully')"
pytest --version

echo "Development environment setup complete!"
echo "To activate: source ${PROJECT_ROOT}/venv/bin/activate"