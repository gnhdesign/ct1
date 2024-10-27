#!/bin/bash

python3 -c "import venv"
ret=$?
if [ $ret -ne 0 ]; then
    echo "Install the the python module venv and then restart this script."
    echo "On Ubuntu:"
    echo "  sudo apt install python3-venv"
    exit 1
fi

mkdir -p .venv
python3 -m venv .venv/
source .venv/bin/activate
pip install -r requirements.txt
deactivate
