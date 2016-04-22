#!venv/bin/python2.7

# Python backend for go-lite-bot, the small Go bot

# Import the Updater class from the nice telegram API wrapper
from telegram.ext import Updater

# Our game-board abstraction
from goboard import Node, Empty, Board

# From the muiltipart business
import httplib
import mimetypes
import urlparse
import uuid

# So we can draw the board
from PIL import Image, ImageDraw, ImageFont
import StringIO
from math import ceil

# So we can save the board
import os.path
from os import mkdir
import cPickle as pickle

# So we can pick random colors
import random 

# Create our Updater
# For ease of configuration, we pull our token from a text file located in the same directory
f = open('token.txt', 'r')
token = f.readline().strip()
f.close()
updater = Updater(token = token)

# Initialize our double reset dict
updater.bot.double_resets = {}

# Convenience for the dispatcher?
dispatcher = updater.dispatcher

# Size of the board
default_board_size = 9

# Directory for save files
save_dir = 'games/'
# If it already exists, just passes
if not os.path.isdir(save_dir):
    mkdir(save_dir)

# Represents the game state, which can be loaded from a file
def get_board(filename):
    if os.path.isfile(save_dir + str(filename) + '.p'):
        f = open(save_dir + str(filename) + '.p', 'rb')
        try:
            out = pickle.load(f)
        except:
            print("Error loading!")
            return Board(default_board_size)
        board = out
        f.close()
    else:
        board = Board(default_board_size)
        f = open(save_dir + str(filename) + '.p', 'wb')
        pickle.dump(board, f, pickle.HIGHEST_PROTOCOL)
        f.close()
    return board

# Helper fuctions
# Note that these contain White/Black game specific stuff, and so are not rolled into the generic class
def score_str(board):
  scores = board.score()
  return "Black: " + str(scores["Black"]) + " White: " + str(scores["White"])

def save_board(board, filename):
    f = open(save_dir + str(filename) + '.p', 'wb')
    try:
        pickle.dump(board, f, pickle.HIGHEST_PROTOCOL)
    except Exception as ex:
        print("Error saving!")
        print("exception: " + str(ex))
    f.close()

# This was taken from the web, and I can't remember where from.
# Need to either attribute or rewrite after learning the standard myself.
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

# End borrowing
 
def are_indices(argList, size):
    if len(argList) != 3:
        return False
    try:
        i = int(argList[1])
        j = int(argList[2])
        if (i <= size and j <= size and i >= 0 and j >= 0):
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
    # Load the board
    board = get_board(update.message.chat_id)

    bot.sendMessage(chat_id=update.message.chat_id, text='```\n' +
                        board.board_str() + '```', parse_mode='Markdown')
    bot.double_resets[str(update.message.chat_id)] = False

dispatcher.addTelegramCommandHandler('getState', print_state)

# Makes a move
def make_move(bot, update, args):
    # Load the board
    board = get_board(update.message.chat_id)

    converted = convert_move(args)
    if ((len(args) != 3 and len(args) != 2) or 
            (not are_indices(converted, board.size))):
        print "Got bad input"
        return

    # We didn't get something that either represented White or Black
    if to_name(converted[0]) == None:
        return

    # If we want it to be empty, then make it so
    # If the space is already empty, do nothing
    if to_name(converted[0]) == Empty:
        if board.get(converted[1],converted[2]) == Empty:
            return
        board.set(to_name(converted[0]),converted[1],converted[2])

    # If the space is empty, go there, otherwise do nothing
    if board.get(converted[1],converted[2]) == Empty:
        board.set(to_name(converted[0]), converted[1], converted[2])
    else:
        return

    # Now that we've moved, save the board and send the new image
    save_board(board, update.message.chat_id)
    send_board_image(bot, update)

    # double_reset nonsense
    bot.double_resets[str(update.message.chat_id)] = False

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
    # Load the board
    board = get_board(update.message.chat_id)

    converted = convert_move(args)
    if ((len(args) != 3 and len(args) != 2) 
            or (not are_indices(converted, board.size))):
        print "Got bad input"
        return

    name = to_name(converted[0])
    row = converted[1]
    col = converted[2]

    # We didn't get something that either represented White or Black
    if name != "Black" and name != "White":
        return

    # Load the board
    board = get_board(update.message.chat_id)
    
    # Check to see if we can flood, and return a message if not
    if board.can_flood(name, row, col):
        board.flood(name, row, col)
        # Save things and send the image
        save_board(board, update.message.chat_id)
        send_board_image(bot, update)
    else:
        bot.sendMessage(chat_id=update.message.chat_id, text="Cannot take starting at " + chr(int(col) + 97).upper() + str(row + 1))

    # double_reset nonsense
    bot.double_resets[str(update.message.chat_id)] = False

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
    global token
    print post_multipart('https://api.telegram.org/bot' + token + '/sendPhoto'
            , [ ('chat_id', str(update.message.chat_id)) ]
            , [ ('photo', 'test-image.png', output.getvalue()) ])

    # double_reset nonsense
    bot.double_resets[str(update.message.chat_id)] = False

dispatcher.addTelegramCommandHandler("photo", send_photo)


# Sends an image of the game board
def send_board_image(bot, update):
    # Load the board
    board = get_board(update.message.chat_id)
    
    space_width = 300
    
    image_dim = (board.size + 3) * space_width
    
    width  = image_dim
    height = image_dim

    wholesize = width - space_width * 4

    img    = Image.new("RGB", (width, height), color="hsl(" + str(random.randrange(0,361)) + ", 100%, 80%)")
    draw   = ImageDraw.Draw(img)
    font   = ImageFont.truetype("Lato-Regular.ttf", int(0.5 * (wholesize / (board.size - 1))))

    def drawBoxAt(x, y, edgelen):
        #Outline
        linewd = int(board.size / 6) * 2
        draw.rectangle([ x, y, x + edgelen, y + edgelen]
                       , fill = "none"
                       , outline = "black")

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
        spacing = space_width

        # We need a background to be able to see the white pieces
        draw.rectangle([x - spacing * 1.5, y - spacing * 1.5, x + wholelen +
            spacing * 1.5, y + wholelen + spacing * 1.5], fill = "burlywood",
            outline = "#7B4A12")
        for i in range(numBoxes):
            for j in range(numBoxes):
                drawBoxAt(x + i * spacing, y + j * spacing, spacing)

        # Draw the labels
        for i in range(board.size):
            draw.text( ( x - 0.75 * spacing - font.getsize(str(i + 1))[0] / 2
                       , y - font.getsize(str(i + 1))[1] / 2 + i * spacing )
                     , str(i + 1)
                     , fill = 'black'
                     , font = font )
            draw.text( ( x + wholelen + 0.75 * spacing -  font.getsize(str(i+1))[0] / 2
                       , y - font.getsize(str(i + 1))[1] / 2 + i * spacing )
                     , str(i + 1)
                     , fill = 'black'
                     , font = font )
        for i in range(board.size):
            draw.text( ( x - font.getsize(chr(i + 97).upper())[0] / 2 + i * spacing
                       , y - spacing )
                     , chr(i + 97).upper()
                     , fill = 'black'
                     , font = font )
            draw.text( ( x - font.getsize(chr(i + 97).upper())[0] / 2 + i * spacing
                       , y + wholelen + spacing - font.getsize('M')[1] )
                     , chr(i + 97).upper()
                     , fill = 'black'
                     , font = font )
        
        # Now we step over the spaces and draw the pieces if need be
        for i in range(board.size):
            for j in range(board.size):
                if board.get(i,j) == "White":
                    drawWhiteAt(x - spacing / 2 + j * spacing, y - spacing / 2 + i * spacing, spacing)
                elif board.get(i,j) == "Black":
                    drawBlackAt(x - spacing / 2 + j * spacing, y - spacing / 2 + i * spacing, spacing) 
                    
    drawBoardAt(space_width * 2, space_width * 2, wholesize, board)

    output = StringIO.StringIO()
    img.save(output, 'PNG')
    global token
    post_multipart('https://api.telegram.org/bot' + token + '/sendPhoto'
            , [ ('chat_id', str(update.message.chat_id)) ]
            , [ ('photo', 'board-image.png', output.getvalue()) ])

    # double_reset nonsense
    bot.double_resets[str(update.message.chat_id)] = False

dispatcher.addTelegramCommandHandler("game", send_board_image)

#Resets everything
def reset_all(bot, update):

    # Check our state
    double_reset = bot.double_resets[str(update.message.chat_id)]

    # Load the board
    board = get_board(update.message.chat_id)

    if double_reset == True:
        board.clear()
        save_board(board, update.message.chat_id)
        bot.double_resets[str(update.message.chat_id)] = False
        send_board_image(bot, update)

def confirm(bot, update):
    bot.double_resets[str(update.message.chat_id)] = True;
    bot.sendMessage( chat_id=update.message.chat_id
                   , text="Send confirm_reset command to reset game state.")

dispatcher.addTelegramCommandHandler("reset_all", confirm)
dispatcher.addTelegramCommandHandler("confirm_reset", reset_all)

# Creates a new game, resizing the board possibly
# Shares the double_reset variable with reset_all
def new_game(bot, update):
    # Check our state
    double_reset = bot.double_resets[str(update.message.chat_id)]

    # Load the board
    board = get_board(update.message.chat_id)

    # If double_reset is a number
    if double_reset != True and double_reset != False:
        # Create a new board and save it
        # Otherwise just clear it
        if board.size != double_reset:
            board = Board(double_reset)
        else:
            board.clear()

        save_board(board, update.message.chat_id)
        bot.double_resets[str(update.message.chat_id)] = False
        send_board_image(bot, update)

def confirm_resize(bot, update, args):
        # See if the number input was valid
        # Only allow up to a 19 x 19 board (arbitrarily chosen)
        try:
            if (len(args) == 1):
                new_size = int(args[0])
        except:
            bot.sendMessage( chat_id=update.message.chat_id
                           , text="Please provide a valid number for the new board size.")
            return

        # Check to make sure the number is okay
        if new_size not in [7, 9, 13, 17, 19]:
            bot.sendMessage( chat_id=update.message.chat_id
                           , text="Please provide a valid number for the new board size.")
            return

        # Remember this number by putting it into the dictionary and ask for
        # confirmation
        bot.double_resets[str(update.message.chat_id)] = new_size
        bot.sendMessage( chat_id=update.message.chat_id
                       , text="Send the confirm_new command to start a new game.")

dispatcher.addTelegramCommandHandler("new_game", confirm_resize)
dispatcher.addTelegramCommandHandler("confirm_new", new_game)

updater.start_polling()
