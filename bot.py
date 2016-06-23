# Simply the class definitions for the bot and worker declarations

# Nice way to make HTTP get requests
import requests

# A nice holder for information we need between function calls
class Bot:
    double_resets = {}

    def __init__ (self, token):
        self.token = token
        handlers = {}

    # Adds a single event handler
    def addHandler (self, text, func):
        handlers[text] = func
    
    # Sends a text message to the specified chat_id
    def sendMessage (self, chat_id = None, text = None):
        if (chat_id != None and text != None):
            r = requests.post('https://api.telegram.org/bot' + self.token +
                              '/sendMessage' +
                              '?chat_id=' + str(chat_id) +
                              '&text='    + text)
            while r.status_code != requests.codes.ok:
                r = requests.post('https://api.telegram.org/bot' + self.token +
                                  '/sendMessage' +
                                  '?chat_id=' + str(chat_id) +
                                  '&text='    + text)
    
    # Sends as photo using multipart-formdata
    # Note that photo is a file-like object (like a StringIO object)
    def sendImage (self, chat_id = None, photo = None):
        if (chat_id != None and photo != None):
            data = { 'chat_id' : str(chat_id) }
            files = { 'photo' : ('board-image.png', photo) }
            requests.post('https://api.telegram.org/bot' + self.token +
                          '/sendPhoto', data = data, files = files)
    
    