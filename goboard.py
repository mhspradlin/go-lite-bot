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