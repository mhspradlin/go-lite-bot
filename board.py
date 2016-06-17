# Contains the Board class, which makes heavy use of the Store abstraction.

# Get the journal store
from store import Store

# Double-ended queue for the flooding mechanism
from collections import deque

# Our events declarations
import events

# The way we will handle representing the game board is in two ways - 
# a graph of piece spaces which are linked to the adjacent spaces, and a 
# two dimensional list which allows direct numerical 
# indexing (hopefully shortcuts)
# Note that the convention is for the edge of the board to have left/up/right/down
# values of None (as appropriate, a corner will only have two Nones, for example)
# and the board will be initialized for all self.player values to be Empty but with
# the adjacent spaces linked up correctly.
# A class (using it like a type) to represent a space where no piece has gone
# Could be a string, but this is a little nicer
class Empty:
    pass

class Node:

    def __init__ (self, player=Empty):
        self.player = player
        self.adjacent = []

# A class to represent a whole board
# Defining it with a field for size to allow for alteration of the board size later
class Board:

    # Initializes a board with Empty nodes
    # First dimension is the row, second is the column
    def __init__ (self, size):
        self.size = size
        self.store = Store(orderMoves)
        self.buildGame(self.store.log())

    # Clears a board
    # Reallocates a Store and rebuilds the game
    def clear (self):
        self.store = Store(orderMoves)
        self.buildGame(self.store.log())

    # Scores a board
    # Returns a dict with all of the player's scores
    # For now, just counts the stones, and apparently empty classes can act an an index. Weird, but okay
    def score (self):
        scores = {}
        for i in range(size):
            for j in range(size):
                scores[self.shortcut[i][j].player] += 1
        return scores

    # Sets a space to be owned by a player
    def set (self, player, row, col):
        if row >= 0 and row < self.size and col >= 0 and col < self.size:
            self.shortcut[row][col].player = player
        return

    # Gets the owner of a space
    def get (self, row, col):
        if row >= 0 and row < self.size and col >= 0 and col < self.size:
            return self.shortcut[row][col].player
        else:
            return None

    # Returns if a space can be flooded for a given player
    def can_flood (self, player, row, col):
        if row >= 0 and row < self.size and col >= 0 and col < self.size:
            # Checks to see if an area can be flooded (is surrounded by nothing but None and the given player)
            # Flooding means removing the pieces from the board, as per the rules of Go
            # Approach is to iteratively flood out from our starting point, using
            # a deque to track items to check and a set to track visited items
            # This is breadth-first.

            # Check on the first entry
            if self.shortcut[row][col].player == player:
                return False

            # Keep track of the Nodes we have yet to visit
            nexts = deque()
            # Keep track of the Nodes we've visited so as not to revisit them
            visited = set()

            # Add ourself to start
            nexts.appendleft((row,col))
            # Also append None to the visited list, which is a really nice way to
            # just pass on the None values
            visited.add(None)

            # Note that len(Set) has constant time complexity, as it does with a
            # list
            while len(nexts) != 0:
                (ci, cj) = nexts.pop()
                cur = self.shortcut[ci][cj]
                if cur not in visited:
                    visited.add(cur)
                    if cur.player != player and cur.player != Empty:
                        nexts.extendleft(cur.adjacent)
                    elif cur.player == Empty:
                        return False
                    else: # cur.player == player
                        pass
                else:
                    pass
            
            # If we make it all the way, then we didn't encounter an empty space in
            # a region surrounded by the given player's pieces and the edge
            return True
        else:
            return False

    # Floods a space for a player
    def flood (self, player, row, col):
        if row >= 0 and row < self.size and col >= 0 and col < self.size:
            # Keep track of the Nodes we have yet to visit
            nexts = deque()
            # Keep track of the Nodes we've visited so as not to revisit them
            visited = set()

            # Add ourself to start
            nexts.appendleft((row,col))
            # Also append None to the visited list, which is a really nice way to
            # just pass on the None values
            visited.add(None)

            # Note that len(Set) has constant time complexity, as it does with a
            # list
            while len(nexts) != 0:
                (ci, cj) = nexts.pop()
                cur = self.shortcut[ci][cj]
                if cur not in visited:
                    visited.add(cur)
                    if cur.player != player and cur.player != Empty:
                        nexts.extendleft(cur.adjacent)
                        cur.player = Empty

    # The buildGame function which builds the game out of an ordered list of 
    # Events. Updates the shortcut array in place.
    # Also returns a value that indicates if the last move (of this log)
    # is a duplicate move.
    def buildGame (self,evts):
        # First we need to walk the events and remove all those which were
        # duplicate moves or undoed
        # To check for duplicates, we build up the game board in concert with
        # processing events. If we reach an undo, we remove the event and
        # rebuild the board.
        # Advantages:
        #   - Not keeping lots of copies of the game board around
        #   - Undoes are common, but usually take up a minority of the events
        # Disadvantages:
        #   - Building the board multiple times, which is especially expensive
        #       for undoes near the end of the game.
        # Other approach:
        #   - Save all copies of the game board as you build, so an undo only
        #       rolls back one board. This seemingly comes with a lower
        #       complexity, but each copy of the board comes with the burden
        #       of allocating the space for a whole board. So, it consumes
        #       dramatically more memory and the speed benefits are not clear.
        
        # Empty the shortcut array
        def empty ():
            # We should return a shortcut array here with interlinked nodes
            # Empty array
            self.shortcut = [[Node() for x in range(self.size)] for x in range(self.size)]
            for i in range(self.size):
                for j in range(self.size):
                    if j > 0:
                        self.shortcut[i][j].adjacent.append((i,j-1))
                    if i > 0:
                        self.shortcut[i][j].adjacent.append((i-1,j))
                    if j < self.size - 1:
                        self.shortcut[i][j].adjacent.append((i,j+1))
                    if i < self.size - 1:
                        self.shortcut[i][j].adjacent.append((i+1,j))
        
        # Add a single move to the shortcut array
        def makeMove (move):
            name, row, col = move[0], move[1], move[2]
            # We already checked to make sure the space is empty, so we can
            # apply
            print("Setting space")
            self.set(name,row,col)
            print("Space set")
            # If we went there, take any zones that are now surrounded 
            # by the player
            # can_flood handles out of bounds indices nicely, so don't 
            # need to filter them here
            for roff in range(-1,2):
                for coff in range(-1,2):
                    if self.can_flood(name, row + roff, col + coff):
                        self.flood(name, row + roff, col + coff)

        # Applies the moves, assuming there are no undoes
        def build (evtList):
            # Applying the moves
            # Note that all events here are now moves (3-tuples)
            for i in range(len(evtList)):
                makeMove(evtList[i])

        empty()
        evtList = []
        sendImage = True
        for i in range(len(evts)):
            (date, evt, args) = evts[i]
            print(evts[i])
            if (evt == events.undo and len(evtList) > 0):
                evtList.pop()
                empty()
                build(evtList)
            elif (evt == events.move):
                print("Making move")
                print(self.shortcut)
                print(self.shortcut[row][col])
                name, row, col = args[0], args[1], args[2]
                # If there isn't already something there and it's within
                # bounds
                if (self.shortcut[row][col] == Empty and
                    row < self.size and col < self.size and
                    row >= 0 and col >= 0):
                    print("Applying move")
                    evtList.append(args)
                    makeMove(args)
                elif (i == len(evts) - 1):
                    # If the last event is invalid, say so
                    print("Invalid last")
                    sendImage = False
                else: # Just ignore
                    print("Invalid move")
            elif (len(evtList) == 0):
                pass
            else: # Something went wrong
                print("Unsupported event in buildGame")
                sendImage = False
        
        # Report if we should respond
        return sendImage
        
    # Adds an event to the journal and rebuilds the shortcut array
    # This is the method that should be used to add events, not get/set
    # Returns whether or not a board image should be sent
    def addEvent (self, evt):
        self.store.insert(evt)
        return self.buildGame(self.store.log())

# Orders moves by UNIX time
def orderMoves ((date1, evt1, args1), (date2, evt2, args2)):
    return date1 < date2
