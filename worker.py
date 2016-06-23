# The worker that processes messages passed to it from the poller.
# Assumes it's one of many workers but has a dedicated queue.
# It's ID is passed to it as an argument.

# Nice way to make HTTP get requests
import requests

# To read arguments
import sys

# For our queues
from collections import deque

# To lock and unlock files
import fcntl

# To read/write files
import os

# To serialize/deserialize objects
import pickle

# To yield
from time import sleep

# Our class definitions
from bot import Bot, Worker

# Our command definitions
from processing import load

# Gives the queue file name for queue i
def queueName (i):
    return queueDir + '/' + str(i) + '_queue.p'

# Check to see if we've been canceled
def canceled ():
    f = open('cancel.txt', 'r')
    done = f.readline.strip()
    f.close()
    return done == 'Yes'

# Gets the queue that was written and write out what's left (hopefully nothing)
# Replaces the work queue
def getMessages ():
    f = open(queueName(ourID), 'r+')
    fcntl.flock(f, fcntl.LOCK_EX)
    workQueue = pickle.load(f)
    pickle.dump(deque(), f, pickle.HIGHEST_PROTOCOL)
    fcntl.flock(f, fcntl.LOCK_UN)
    f.close()

# Package as a function to be run in go-lite-bot.py
def run ():
    # For ease of configuration, we pull our token from a text file located in the same directory
    f = open('token.txt', 'r')
    token = f.readline().strip()
    f.close()

    # Process our arguments, which should be safe since they're passed by start
    queueDir = sys.argv[1]
    ourID    = int(sys.argv[2])

    # Our overall work queue
    workQueue = deque()

    # Initialize our bot
    bot = Bot(token)

    # Load all of our event handlers into our Worker
    load(bot)

    # Continually process incoming updates
    while not canceled():
        getMessages()
        for i in range(len(workQueue)):
            update = workQueue[i]
            # Only process if it's a command
            if update.message.text[0] == '/':
                command = update.message.text[1:].split()[0]
                if command in bot.handlers:
                    args = update.message.text[1:].split()[1:]
                    bot.handlers[command](bot, update, args)



