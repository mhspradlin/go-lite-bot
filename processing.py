# Python backend for go-lite-bot, the small Go bot

# Should really use the fnctl package with the flock() function
# to place locks on the files being read. Setting read/write locks as appropriate
# will allow multiple instances to access the same filesystem for reading and
# writing files. A really extensible solution might access a database
# instead, but that's not necessary for now.

# Our game-board abstraction
from board import Node, Empty, Board

# So we can draw the board
from PIL import Image, ImageDraw, ImageFont
from io import StringIO
from math import ceil

# So we can save the board
import os.path
from os import mkdir
import pickle

# So we can pick random colors
import random 

# Events names
import events

# To lock and unlock files
import fcntl

# Things to put our definitions into
from bot import Bot

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
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            out = pickle.load(f)
        except:
            print("Error loading!")
            return Board(default_board_size)
        board = out
    else:
        board = Board(default_board_size)
        f = open(save_dir + str(filename) + '.p', 'wb')
        pickle.dump(board, f, pickle.HIGHEST_PROTOCOL)
    fcntl.flock(f, fcntl.LOCK_UN)
    f.close()
    return board

# Helper fuctions
# Note that these contain White/Black game specific stuff, and so are not rolled into the generic class
def score_str(board):
  scores = board.score()
  return "Black: " + str(scores["Black"]) + " White: " + str(scores["White"])

def save_board(board, filename):
    f = open(save_dir + str(filename) + '.p', 'wb')
    fcntl.flock(f, fcntl.LOCK_EX)
    try:
        pickle.dump(board, f, pickle.HIGHEST_PROTOCOL)
    except Exception as ex:
        print("Error saving!")
        print("exception: " + str(ex))
    fcntl.flock(f, fcntl.LOCK_UN)
    f.close()
 
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

# Makes a move
def make_move(bot, update, args):
    # Load the board
    board = get_board(update.message.chat_id)

    converted = convert_move(args)
    if ((len(args) != 3 and len(args) != 2) or 
            (not are_indices(converted, board.size))):
        print("Got bad input")
        return
    
    # The date of the update for our journal
    # The update_id is an authoritative ordering like a date
    date = update.update_id

    # Name our positions
    name = to_name(converted[0])
    row = converted[1]
    col = converted[2]

    # We didn't get something that either represented White or Black
    if name == None:
        return

    # Apply the move, noting whether or not to send an image
    sendImage = board.addEvent((date, events.move, (name, row, col)))

    # Now that we've moved, save the board and send the new image if appropriate
    save_board(board, update.message.chat_id)
    if (sendImage):
        send_board_image(bot, update)

    # double_reset nonsense
    bot.double_resets[str(update.message.chat_id)] = False

def bmove(bot, update, args):
    make_move(bot, update, ["Black"] + args)
def wmove(bot, update, args):
    make_move(bot, update, ["White"] + args)

# Undo the last action
def undo (bot, update, args):
    # Load the board
    board = get_board(update.message.chat_id)

    # The date of the update for our journal
    # The update_id is an authoritative ordering like a date
    date = update.update_id

    # Apply the undo
    board.addEvent((date, events.undo, None))

    # Now that we've undoed, save the board and send the new image
    save_board(board, update.message.chat_id)
    send_board_image(bot, update)

    # double_reset nonsense
    bot.double_resets[str(update.message.chat_id)] = False

# Sends an image of the game board
def send_board_image(bot, update):
    # Load the board
    board = get_board(update.message.chat_id)
    
    # Empirically determined, this seems to look fine with the JPG compression that Telegram does
    space_width = 60
    
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
                       , fill = None
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
    bot.sendImage(chat_id = str(update.message.chat_id), photo = output)

    # double_reset nonsense
    bot.double_resets[str(update.message.chat_id)] = False

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
        # See if the number input was valid (or no number was input)
        # Only allow up to a 19 x 19 board (arbitrarily chosen)
        if (len(args) == 0): # Don't change the size
            new_size = get_board(update.message.chat_id).size
            bot.double_resets[str(update.message.chat_id)] = new_size
        elif (len(args) == 1):
            try:
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

# The function that exposes the appropriate loading method
def load (bot):
    # Start response
    bot.addHandler('start', start)

    # Move commands
    bot.addHandler('move', make_move)
    bot.addHandler('bmove', bmove)
    bot.addHandler('Bmove', bmove)
    bot.addHandler('BMove', bmove)
    bot.addHandler('wmove', wmove)
    bot.addHandler('Wmove', wmove)
    bot.addHandler('WMove', wmove)
    bot.addHandler('bmvoe', bmove)
    bot.addHandler('Bmvoe', bmove)
    bot.addHandler('BMvoe', bmove)
    bot.addHandler('wmvoe', wmove)
    bot.addHandler('Wmvoe', wmove)
    bot.addHandler('WMvoe', wmove)
    # And shortcuts!
    bot.addHandler('b', bmove)
    bot.addHandler('w', wmove)

    # Undo
    bot.addHandler('undo', undo)

    # Send the board image
    bot.addHandler("game", send_board_image)

    # Making new games
    bot.addHandler("new_game", confirm_resize)
    bot.addHandler("confirm_new", new_game)