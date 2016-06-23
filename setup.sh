#!/bin/bash

# Installs the right Python versions
apt-get install python3-dev python3-setuptools

# Sets up the virtualenv right
virtualenv --no-site-packages -p python3 venv

# Sets up packages appropriately for the bot
source venv/bin/activate
pip3 install pillow
pip3 install requests

# Installs the fonts needed
apt-get install libfreetype6-dev