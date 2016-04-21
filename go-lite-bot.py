#!venv/bin/python2.7

# Python backend for go-lite-bot, the small Go bot

# Import the Updater class from the nice telegram API wrapper
from telegram.ext import Updater

# From the muiltipart business
import httplib
import mimetypes
import urlparse
import uuid

from PIL import Image, ImageDraw, ImageFont

import StringIO

import os.path
import pickle
import random 

# Double-ended queue for the flooding mechanism
from collections import deque

# Create our Updater
updater = Updater(token = 'TOKEN')

# Convenience for the dispatcher?
dispatcher = updater.dispatcher

# Size of the board
board_size = 9

# Image dimensions
image_dim = 1050

# Name of the save file
saved_board = 'saved_board.p'

# The way we will handle representing the game board is in two ways - 
# a graph of piece spaces which are linked to the adjacent spaces, and a 
# two dimensional list which allows direct numerical 
# indexing (hopefully shortcuts)
# Note that the convention is for the edge of the board to have left/up/right/down
# values of None (as appropriate, a corner will only have two Nones, for example)
# and the board will be initialized for all self.player values to be Empty but with
# the adjacent spaces linked up correctly.
class Node:

    def __init__(self, player):
        self.player = player
        self.left  = None
        self.up    = None
        self.right = None
        self.down  = None

    # Checks to see if an area can be flooded (is surrounded by nothing but None and the given player)
    # Flooding means removing the pieces from the board, as per the rules of Go
    def can_flood(self, player):
        # Approach is to iteratively flood out from our starting point, using
        # a deque to track items to check and a set to track visited items
        # This is breadth-first.

        # Check on the first entry
        if self.player == player:
            return False

        # Keep track of the Nodes we have yet to visit
        nexts = deque()
        # Keep track of the Nodes we've visited so as not to revisit them
        visited = set()

        # Add ourself to start
        nexts.appendleft(self)
        # Also append None to the visited list, which is a really nice way to
        # just pass on the None values
        visited.add(None)

        # Note that len(Set) has constant time complexity, as it does with a
        # list
        while len(nexts) != 0:
            cur = nexts.pop()
            if cur not in visited:
                visited.add(cur)
                if cur.player != player and cur.player != Empty:
                    nexts.extendleft([cur.left, cur.up, cur.right, cur.down])
                elif cur.player == Empty:
                    return False
                else: # cur.player == player
                    pass
            else:
                pass
        
        # If we make it all the way, then we didn't encounter an empty space in
        # a region surrounded by the given player's pieces and the edge
        return True

    # Floods a contiguous group of another player's pieces
    def flood(self, player):
        if self.player != player and self.player != Empty:
            self.player = Empty
            if self.left   != None:
                self.left.flood(player)
            if self.up     != None:
                self.up.flood(player)
            if self.right  != None:
                self.right.flood(player)
            if self.down   != None:
                self.down.flood(player)

# A class (using it like a type) to represent a space where no piece has gone
# Could be a string, but this is a little nicer
class Empty:
    pass

# A class to represent a whole board
# Defining it with a field for size to allow for alteration of the board size later
class Board:

    # Initializes a board with Empty nodes
    # First dimension is the row, second is the column
    def __init__(self, size):
        self.size = size
        self.shortcut = [[Node(Empty) for x in range(size)] for x in range(size)]
        for i in range(size):
            for j in range(size):
                if j > 0:
                    self.shortcut[i][j].left  = self.shortcut[i][j-1]
                if i > 0:
                    self.shortcut[i][j].up    = self.shortcut[i-1][j]
                if j < size - 1:
                    self.shortcut[i][j].right = self.shortcut[i][j+1]
                if i < size - 1:
                    self.shortcut[i][j].down  = self.shortcut[i+1][j]

    # Clears a board
    # Just set everything to Empty, no need to reallocate memory
    def clear(self):
        for i in range(self.size):
            for j in range(self.size):
                self.shortcut[i][j].player = Empty

    # Scores a board
    # Returns a dict with all of the player's scores
    # For now, just counts the stones, and apparently empty classes can act an an index. Weird, but okay
    def score(self):
        scores = {}
        for i in range(size):
            for j in range(size):
                scores[self.shortcut[i][j].player] += 1
        return scores

    # Returns a string that represents the board
    def board_str(self):
        msg = ""
        for i in range(self.size):
            for j in range(self.size):
                name = "E" if self.shortcut[i][j].player == Empty else self.shortcut[i][j].player[0]
                msg += name
                msg += " "
            msg += "\n"
        return msg

    # Sets a space to be owned by a player
    def set(self, player, row, col):
        if row >= 0 and row < self.size and col >= 0 and col < self.size:
            self.shortcut[row][col].player = player
        return

    # Gets the owner of a space
    def get(self, row, col):
        if row >= 0 and row < self.size and col >= 0 and col < self.size:
            return self.shortcut[row][col].player
        else:
            return None

    # Returns if a space can be flooded for a given player
    def can_flood(self, player, row, col):
        if row >= 0 and row < self.size and col >= 0 and col < self.size:
            return self.shortcut[row][col].can_flood(player)
        else:
            return False

    # Floods a space for a player
    def flood(self, player, row, col):
        if row >= 0 and row < self.size and col >= 0 and col < self.size:
            self.shortcut[row][col].flood(player)
        return

# Represents the game state, which can be loaded from a file
def get_board():
    if os.path.isfile(saved_board):
        f = open(saved_board, 'r')
        out = pickle.load(f)
        board = out
        f.close()
    else:
        board = Board(board_size)
        f = open(saved_board, 'w')
        pickle.dump(board, f)
        f.close()
    return board

# Helper fuctions
# Note that these contain White/Black game specific stuff, and so are not rolled into the generic class
def score_str(board):
  scores = board.score()
  return "Black: " + str(scores["Black"]) + " White: " + str(scores["White"])

def save_board(board):
    f = open(saved_board, 'w')
    pickle.dump(board, f)
    f.close()

def post_multipart(url, fields, files):
    parts = urlparse.urlparse(url)
    scheme = parts[0]
    host = parts[1]
    selector = parts[2]
    content_type, body = encode_multipart_formdata(fields, files)
    if scheme == 'http':
        h = httplib.HTTP(host)
    elif scheme == 'https':
        h = httplib.HTTPS(host)
    else:
        raise ValueError('unknown scheme: ' + scheme)
    h.putrequest('POST', selector)
    h.putheader('content-type', content_type)
    h.putheader('content-length', str(len(body)))
    h.endheaders()
    h.send(body)
    errcode, errmsg, headers = h.getreply()
    return h.file.read()
 
def encode_multipart_formdata(fields, files):
    def get_content_type(filename):
        return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

    LIMIT = '----------' + uuid.uuid4().hex
    CRLF = '\r\n'
    L = []
    for (key, value) in fields:
        L.append('--' + LIMIT)
        L.append('Content-Disposition: form-data; name="%s"' % key)
        L.append('')
        L.append(value)
    for (key, filename, value) in files:
        L.append('--' + LIMIT)
        L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
        L.append('Content-Type: %s' % get_content_type(filename))
        L.append('')
        L.append(value)
    L.append('--' + LIMIT + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % LIMIT
    return content_type, body
 
def are_indices(argList):
    if len(argList) != 3:
        return False
    try:
        i = int(argList[1])
        j = int(argList[2])
        if (i <= board_size and j <= board_size and i >= 0 and j >= 0):
            return True
        return False
    except ValueError:
        return False

# Converts from human readible to computer friendly
def convert_move(args):
    if (len(args) != 3 and len(args) != 2):
        return args
    ret = [args[0], 0, 0]
    if (len(args) == 3):
        j = args[1]
    else:
        j = args[1][0]
    ret[2] = ord(j.lower()) - 97
    try:
        if (len(args) == 2 and len(args[1]) >= 2):
            ret[1] = int(args[1][1:]) - 1
            return ret
        elif len(args) == 3:
            ret[1] = int(args[2]) - 1
            return ret
        else:
            return args
    except ValueError:
        return args

# Turns any shorthand string into a nice named string
def to_name(name):
    if name == "Black" or name == "White":
        return name
    else:
        lower = name.lower()
        if lower == "w" or lower == "white":
            return "White"
        if lower == "b" or lower == "black":
            return "Black"
        if lower == "o" or lower == "empty":
            return Empty
        else:
            return None

def start(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text="Hey there!")

dispatcher.addTelegramCommandHandler('start', start)

# Prints current game state
def print_state(bot, update):
    #print "Trying to send message: " + msg
    bot.sendMessage(chat_id=update.message.chat_id, text='```\n' +
                        bot.board.board_str() + '```', parse_mode='Markdown')
    global double_reset
    double_reset = False

dispatcher.addTelegramCommandHandler('getState', print_state)

# Makes a move
def make_move(bot, update, args):
    converted = convert_move(args)
    if ((len(args) != 3 and len(args) != 2) or (not are_indices(converted))):
        print "Got bad input"
        return

    # We didn't get something that either represented White or Black
    if to_name(converted[0]) == None:
        return

    # If we want it to be empty, then make it so
    # If the space is already empty, do nothing
    if to_name(converted[0]) == Empty:
        if bot.board.get(converted[1],converted[2]) == Empty:
            return
        bot.board.set(to_name(converted[0]),converted[1],converted[2])

    # If the space is empty, go there, otherwise do nothing
    if bot.board.get(converted[1],converted[2]) == Empty:
        bot.board.set(to_name(converted[0]), converted[1], converted[2])
    else:
        return

    # Now that we've moved, save the board and send the new image
    save_board(bot.board)
    #print_state(bot, update)
    send_board_image(bot, update)

    # double_reset nonsense
    global double_reset
    double_reset = False

def bmove(bot, update, args):
    make_move(bot, update, ["Black"] + args)
def wmove(bot, update, args):
    make_move(bot, update, ["White"] + args)
def omove(bot, update, args):
    make_move(bot, update, ["o"] + args)

dispatcher.addTelegramCommandHandler('move', make_move)
dispatcher.addTelegramCommandHandler('bmove', bmove)
dispatcher.addTelegramCommandHandler('Bmove', bmove)
dispatcher.addTelegramCommandHandler('BMove', bmove)
dispatcher.addTelegramCommandHandler('wmove', wmove)
dispatcher.addTelegramCommandHandler('Wmove', wmove)
dispatcher.addTelegramCommandHandler('WMove', wmove)
dispatcher.addTelegramCommandHandler('moveo', omove)
dispatcher.addTelegramCommandHandler('moveO', omove)

# Tries to flood for a player
def flood_space(bot, update, args):
    converted = convert_move(args)
    if ((len(args) != 3 and len(args) != 2) or (not are_indices(converted))):
        print "Got bad input"
        return

    name = to_name(converted[0])
    row = converted[1]
    col = converted[2]

    # We didn't get something that either represented White or Black
    if name != "Black" and name != "White":
        return
    
    # Check to see if we can flood, and return a message if not
    if bot.board.can_flood(name, row, col):
        bot.board.flood(name, row, col)
        # Save things and send the image
        save_board(bot.board)
        send_board_image(bot, update)
    else:
        bot.sendMessage(chat_id=update.message.chat_id, text="Cannot take starting at " + chr(int(col) + 97).upper() + str(row + 1))

    # double_reset nonsense
    global double_reset
    double_reset = False

def bflood(bot, update, args):
    flood_space(bot, update, ["Black"] + args)
def wflood(bot, update, args):
    flood_space(bot, update, ["White"] + args)

dispatcher.addTelegramCommandHandler('btake', bflood)
dispatcher.addTelegramCommandHandler('bTake', bflood)
dispatcher.addTelegramCommandHandler('Btake', bflood)
dispatcher.addTelegramCommandHandler('BTake', bflood)
dispatcher.addTelegramCommandHandler('wtake', wflood)
dispatcher.addTelegramCommandHandler('wTake', wflood)
dispatcher.addTelegramCommandHandler('Wtake', wflood)
dispatcher.addTelegramCommandHandler('WTake', wflood)
dispatcher.addTelegramCommandHandler('take' , flood_space)

# Sends a photo
def send_photo(bot, update):
    img = Image.new('RGB', (512, 512))
    pixels = [i + j for i in range(512) for j in range(512)]
    img.putdata(pixels)
    output = StringIO.StringIO()
    img.save(output, 'PNG')
    #msg = encode_multipart_formdata(
    #        [ ('chat-id', str(update.message.chat_id)) ]
    #        , [ ('photo', 'test-image.png', output.getvalue()) ])
    #print msg
    # Library code is broken...
    #bot.sendPhoto(chat_id=update.message.chat_id, photo=msg)
    #Workaround
    print post_multipart('https://api.telegram.org/bot215378074:AAHv1Ks44hVQ2nfjqUbRtI6rfkcCtZqjxeU/sendPhoto'
            , [ ('chat_id', str(update.message.chat_id)) ]
            , [ ('photo', 'test-image.png', output.getvalue()) ])
    global double_reset
    double_reset = False

dispatcher.addTelegramCommandHandler("photo", send_photo)


# Sends an image of the game board
def send_board_image(bot, update):
    width  = image_dim
    height = image_dim

    img    = Image.new("RGB", (width, height), color="hsl(" + str(random.randrange(0,361)) + ", 100%, 80%)")
    draw   = ImageDraw.Draw(img)
    font   = ImageFont.truetype("Lato-Regular.ttf", 40)
    font2  = ImageFont.truetype("Lato-Regular.ttf", 16)
    def drawBoxAt(x, y, edgelen):
        #Outline
        draw.line([ (x, y), (x + edgelen, y), (x + edgelen, y + edgelen)
                  , (x, y + edgelen), (x,y) ], fill = "black")

    # Note that the circles are specified from their upper left corner
    def drawWhiteAt(x, y, cellwidth):
        draw.ellipse([ (x + cellwidth / 10, y + cellwidth / 10)
                     , (x + 9 * cellwidth / 10, y + 9 * cellwidth / 10) ],
                     outline = "white", fill = "white")
    def drawBlackAt(x, y, cellwidth):
        draw.ellipse([ (x + cellwidth / 10, y + cellwidth / 10)
                     , (x + 9 * cellwidth / 10, y + 9 * cellwidth / 10) ],
                     outline = "black", fill = "black")

    def drawBoardAt(x, y, wholelen, board):
        # We'll say the board starts/ends 10% in from each side
        # Also, note that there are size - 2 boxes in each dimension to make the correct number
        # of crossed spaces
        numBoxes = board.size - 1
        spacing = wholelen / numBoxes

        # We need a background to be able to see the white pieces
        draw.rectangle([x - spacing * 1.5, y - spacing * 1.5, x + wholelen +
            spacing * 1.5, y + wholelen + spacing * 1.5], fill = "burlywood",
            outline = "#7B4A12")
        for i in range(numBoxes):
            for j in range(numBoxes):
                drawBoxAt(x + i * spacing, y + j * spacing, spacing)

        # Draw the labels
        for i in range(board.size):
            draw.text((x - spacing + font.getsize("D")[0] / 2, y - font.getsize(str(i + 1))[1] / 2 + i * spacing), str(i + 1), fill = 'black', font = font)
            draw.text((x + wholelen + spacing - 3 * font.getsize("D")[0] / 2, y - font.getsize(str(i + 1))[1] / 2 + i * spacing), str(i + 1), fill = 'black', font = font)
        for i in range(board.size):
            draw.text((x - font.getsize(chr(i + 97).upper())[0] / 2 + i * spacing, y - spacing), chr(i + 97).upper(), fill = 'black', font = font)
            draw.text((x - font.getsize(chr(i + 97).upper())[0] / 2 + i * spacing, y + wholelen + spacing - font.getsize(chr(i + 97).upper())[1]), chr(i + 97).upper(), fill = 'black', font = font)
        
        # Now we step over the spaces and draw the pieces if need be
        for i in range(board.size):
            for j in range(board.size):
                if board.get(i,j) == "White":
                    drawWhiteAt(x - spacing / 2 + j * spacing, y - spacing / 2 + i * spacing, spacing)
                elif board.get(i,j) == "Black":
                    drawBlackAt(x - spacing / 2 + j * spacing, y - spacing / 2 + i * spacing, spacing) 

    wholesize = width * 0.6
    drawBoardAt(width * 0.2, width * 0.2, wholesize, bot.board)

    output = StringIO.StringIO()
    img.save(output, 'PNG')
    post_multipart('https://api.telegram.org/bot215378074:AAHv1Ks44hVQ2nfjqUbRtI6rfkcCtZqjxeU/sendPhoto'
            , [ ('chat_id', str(update.message.chat_id)) ]
            , [ ('photo', 'board-image.png', output.getvalue()) ])
    global double_reset
    double_reset = False

dispatcher.addTelegramCommandHandler("game", send_board_image)

double_reset = False

#Resets everything
def reset_all(bot, update):
    global double_reset
    if double_reset:
        if board_size != bot.board.size:
            bot.board = Board(board_size)
            save_board(bot.board)
            double_reset = False
            send_board_image(bot, update)
        else:
            bot.board.clear()
            save_board(bot.board)
            double_reset = False
            send_board_image(bot, update)

def confirm(bot, update):
    global double_reset
    double_reset = True;
    bot.sendMessage(chat_id=update.message.chat_id, text="Send confirm_reset command to reset game state.")

dispatcher.addTelegramCommandHandler("reset_all", confirm)
dispatcher.addTelegramCommandHandler("confirm_reset", reset_all)

updater.bot.board = get_board()
updater.start_polling()
