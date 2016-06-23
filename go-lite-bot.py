#!venv/bin/python3

# Python backend for go-lite-bot, the small Go bot

# So we can get our arguments
import sys

# So we can save the board
import os.path
from os import mkdir, fork
import cPickle as pickle

# To lock and unlock files
import fcntl

# The queues
from collections import deque

# The worker functions
import worker

# The poller functions
import poller

# Size of the board
default_board_size = 9

# Directory for save files
save_dir = 'games/'
# If it already exists, just passes
if not os.path.isdir(save_dir):
    mkdir(save_dir)

# Process our arguments
numWorkers = sys.argv[1]

# Initialize the worker queues
if not os.path.isdir('queues/'):
    mkdir('queues')
for i in range(numWorkers):
    f = open('queues/' + str(i) + '_queue.p')
    pickle.dump(deque(), f, pickle.HIGHEST_PROTOCOL)
    f.close()

# Start the poller and workers
val = os.fork()

# If the child
if val == 0:
    worker.run()
else: # The parent, and we should run the poller
    poller.run()