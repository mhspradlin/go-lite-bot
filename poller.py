# The poller that queries Telegram for bot updates.
# Assumes it's the only poller enqueueing elements onto a number of queues.

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

# Package as a function for go-lite-bot to run
def run ():
    # For ease of configuration, we pull our token from a text file located in the same directory
    f = open('token.txt', 'r')
    token = f.readline().strip()
    f.close()

    # Get the last update number so we don't do duplicates
    f = open('offset.txt', 'r')
    offset = int(f.readline.strip())
    f.close()

    # Process our arguments, which should be safe since they're passed by start
    queueDir = sys.argv[1]
    numQueues = int(sys.argv[2])

    # Initialize our internal buffers to hold pending writes
    writeBuffers = []
    for i in range(numQueues):
        writeBuffers.append(deque())

    # Continually request updates and pass them to the queues
    while not canceled():
        updates = getUpdates()
        # If there's no updates, yield
        if len(updates) == 0:
            sleep(0)
        else: # Apply them to the queues and write
            for i in range(updates):
                if  'message' in updates[i] and 'text' in updates[i].message:
                    writeBuffers[hash(updates[i].message.chat.id) % numQueues].append(updates[i])
            writeOut()

# Gives the queue file name for queue i
def queueName (i):
    return queueDir + '/' + str(i) + '_queue.p'

# Write out the new offset number
def writeOffset (num):
    f = open('offset.txt', 'w')
    f.write(str(num))
    f.close()

# Check to see if we've been canceled
def canceled ():
    f = open('cancel.txt', 'r')
    done = f.readline.strip()
    f.close()
    return done == 'Yes'

# Write out all buffers, appending elements to the appropriate queues
def writeOut ():
    for i in range(len(writeBuffers)):
        f = open(queueName(i), 'r+')
        fcntl.flock(f, fcntl.LOCK_EX)
        workingQueue = pickle.load(f)
        # Recall that later messages are at higher indices
        # Workers read messages off the left, so we should add to the right
        # in ascending order
        for j in range(len(writeBuffers[i])):
            workingQueue.append(writeBuffers[i].popLeft())
        pickle.dump(writeBuffers[i], f, pickle.HIGHEST_PROTOCOL)
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()

# Get all updates from the server for our bot
def getUpdates ():
    r = requests.get('https://api.telegram.org/bot' + token + '/getUpdates' + 
                     '?offset=' + str(offset) +
                     '&limit=100')
    # Updates are returned sequentially, update the offset
    updates = r.json()
    if (len(updates) > 0):
        offset = updates[len(updates) - 1].update_id + 1
        # Write out offset counter
        writeOffset(offset)
    return updates

