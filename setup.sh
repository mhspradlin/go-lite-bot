#!/bin/bash

# Sets up the virtualenv right
virtualenv --no-site-packages venv

# Sets up packages appropriately for the bot
source venv/bin/activate
pip install python-telegram-bot
pip install pillow

# Installs the fonts needed
apt-get install libfreetype6-dev