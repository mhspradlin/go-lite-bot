# Contains the top-level class and interface declarations for the journal store.

# A journal store, which consists of
#   * An ordered log of events
#   * A function to generate output from event streams
#   * Cached output at various event stream times (TODO)
class Store:
    
    ''' No class variables are needed. '''

    # Initializes an empty Store
    def __init__ (self, orderFunc=None, builder=None, initList=[]):
        # Order is important and the most frequently accessed items are at the
        # front, so we use a list here. We don't gain anything by using a deque
        # or a Dict according to 
        # https://wiki.python.org/moin/TimeComplexity
        self.journal = initList

        # It's okay if this is None, as we will assume that the caller just
        # wants to use the journal and will build the output themselves.
        self.builder = builder

        # If this is None, we hope for the best that there's a < function
        # defined on the list elements
        self.orderFunc = orderFunc

    # Insert an element to the journal
    def insert (self, elem):
        if (self.orderFunc != None):
            print(self.orderFunc)
            print(self.journal)
            print(elem)
            # If we can add to the end, do so (constant time)
            if (len(self.journal) == 0 or self.orderFunc(self.journal[len(self.journal)-1],elem)):
                self.journal.append(elem)
            else: # Walk backwards until we can insert (linear time)
                i = len(self.journal) - 2
                while (self.orderFunc(elem, self.journal[i])):
                    i -= 1
                self.journal.insert(i+1,elem)
            print(self.journal)
            return True
        else: # Hope there's a < operation (should catch errors)
            if (self.journal[len(self.journal)-1] < elem):
                self.journal.append(elem)
            else:
                i = len(self.journal) - 2
                while (elem < self.journal[i]):
                    i -= 1
                self.journal.insert(i+1,elem)
            return True
                
    # Return the journal
    def log (self):
        return self.journal
    
    # Produce the output, if possible. Allow the user to pass a different
    # builder function if they'd like, which could be useful for certain
    # applications.
    def output (self, builder=None):
        if (builder == None):
            if (self.builder == None):
                return None
            else:
                return self.builder(self.journal)
        else:
            return builder(self.journal)

    # Set a new order function
    def setOrderFunc (self, orderFunc):
        self.orderFunc = orderFunc

    # Set a new builder
    def setBuilder (self, builder):
        self.builder = builder
