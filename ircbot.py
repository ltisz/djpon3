import socket
import sys

class IRCBot:
    irc = socket.socket()
    
    def __init__(self):
        self.irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    #Message sending function
    def send(self, chan, msg): 
        self.irc.send(bytes("PRIVMSG " + chan + " " + msg + "\r\n","UTF-8"))

    def quit(self):
        self.irc.send(bytes("QUIT\r\n","UTF-8"))
        
    #IRC Connection. channels variable must be a LIST of channels to join.
    def connect(self, server, channels, botnick, pw):
        userstring = "USER " + botnick + " trixie lulamoon :dj-p0n3 v2.0 - Your all purpose dubstep pone waifu\r\n"
        nickstring = "NICK " + botnick + "\r\n"
        versionstring = "VERSION PonyBot v0.7.4\r\n" 
        avatarstring = "METADATA * SET avatar https://trixi.cc/djpone.png"
        self.irc.connect((server,6667))
        self.irc.send(userstring.encode("UTF-8"))
        self.irc.send(nickstring.encode("UTF-8"))
        delay = 1 #Set delay to make sure bot does initial ping/version/ident before joining channels
        while delay == 1:
            text = self.irc.recv (4096).decode("UTF-8")
            text = text.strip("\n\r")
            print(text)
            if "PING" in text: #pingpong
                print("Recieved ping")
                self.irc.send (bytes("PONG " + text.split()[1] + "\r\n", "UTF-8"))
            if "VERSION" in text:
                self.irc.sendall (versionstring.encode("UTF-8"))
                print("VERSION reply")
            if "MODE " + botnick in text:
                delay = 0
                self.irc.send (bytes(" PRIVMSG NickServ :identify " + pw + "\r\n", "UTF-8"))
                for chan in channels:
                    self.irc.send (bytes("JOIN :" + chan + "\r\n","UTF-8"))
        #self.irc.send(avatarstring.encode("UTF-8"))
    #Receiving irc data
    def get_text(self):
        text = self.irc.recv(2048).decode("UTF-8")
        text = text.strip('\n\r')
        if text.find("PING") != -1:
            self.irc.send(bytes("PONG " + text.split()[1] + "\r\n", "UTF-8"))
        
        if text.find("VERSION") != -1:
            print("version req")
            self.irc.send(versionstring.encode("UTF-8"))

        return text

    def timecruncher(self,tyme):
        x = 0
        fract = ''
        numlist = {}
        accept = ['s','m','d','y','h','w']
        good = 1
        while x < len(tyme):
            try:
                int(tyme[x])
                fract = fract+tyme[x]
                x+=1
            except:
                if tyme[x] in accept:
                    numlist[tyme[x]]=fract
                    fract = ''
                    x+=1
                else:
                    good = 0
                    x+=1
        if good == 0:
            return 0
        else:
            print(numlist)
            total = 0
            denoms = {'s':1,'m':60,'h':3600,'w':604800,'d':86400,'y':31536000}
            for entry in numlist:
                total = total + (int(numlist[entry])*denoms[entry])
            return total

