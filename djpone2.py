from ircbot import *
from nltk import *
from collections import defaultdict
import os
import sys
import random
import csv
from urllib.parse import quote
from urllib.request import urlopen, urlretrieve
from urllib.error import HTTPError
from dotenv import load_dotenv
import datetime
import html
import json
import threading
import requests
from bs4 import BeautifulSoup
import time
import pytz
import math
import xml.etree.ElementTree as ET
from geopy import geocoders
import tweepy
import traceback
import mysql.connector
import string

### IRC INFO
channels = ["#kame-house","#death","#ponycafe","#cupcake","#equestria","#titties"]
#channels = ["#equestria"]
channel = ""
server = "moo.slashnet.org"
irc = IRCBot()
load_dotenv()
if len(sys.argv)>1:
    if str(sys.argv[1]) == "test":
        print("Starting test terminal\r\n")
        testMode = True
else:
    testMode = False

### TIMER VARIABLES
central = pytz.timezone("America/Chicago")
timenow = central.localize(datetime.datetime.now().replace(microsecond=0))
TD0 = datetime.timedelta(0)
fmtsOrderz = ['{0} {1}', '{1} {0}', '{0}', '{1}']
fmtsTime = ['%H:%M', '%I:%M%p', '%I%p', '%I:%M %p', '%I%M%p', '%I%M %p', '%H%M']
fmtsDate = ['%m/%d/%y', '%m/%d/%Y', '0%m/%d/%y', '0%m/%d/%Y', '%m/%d', '0%m/%d']

### VARIOUS NEEDED THINGS
grepEscape = ["\\",'"',"$",".","^","[","]","{","}","?","+","(",")"]
gn = geocoders.GeoNames(username=os.environ.get('geouser'))
forbiddenTweets = ["die","kill","murder","death","cunt","fuck","suicide","rape"]
cleanr = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')
imageTypes = ["png","jpg","gif"]

### HEADERS ##
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
tweetHeaders = {"Authorization": "Bearer {}".format(os.environ.get('bearer_token'))}

auth = tweepy.OAuthHandler(os.environ.get('consumer_token'), os.environ.get('consumer_token_private'))
auth.set_access_token(os.environ.get('tweekey'), os.environ.get('tweesecret'))
api = tweepy.API(auth)

### COMMANDS ###
poneCommands = ["$quote", "$mention", "$Quote", "$Mention",                         #0-3
                "$first mention", "$last mention", "$first quote", "$last quote",   #4-7
                "$first Mention", "$last Mention", "$first Quote", "$last Quote",   #8-11
                "$hey", "$explain", "$ponyall", "$pony",                            #12-15
                "$remind", "$paheal", "$rule34", "$dan",                            #16-19
                "$wiki", "$page", "$korannext", "$koran",                           #20-23
                "$bible", "$all","$stock", "$nook",                                 #24-27
                "$garf", "$pluggers", "$sup", "$tweet",                             #28-31
                "$aqi", "$gis", "$g", "$yt",                                        #32-35
                "$we", "$adom", "$next", "$timer",                                  #36-39
                "$timeleft", "$choose", "$tell", "$tv_next",                        #40-43
                "$tv_last", "$honk", "$commandlist", "$help",                       #44-47
                "$fun milo", "$bogpill", "$rand", "$legalweed",                     #48-51
                "$urwfeels","$commandlist","!search"]                               #52-54

flexCommands = ["$bible","$koran","$we","$aqi", "$pluggers","$garf","$hey","$timeleft","$honk"]

noInput = ["$help", "$korannext", "$bogpill", "$page",
           "$fun milo", "$explain", "$next", "$wiki",
           "$rand", "$legalweed", "$urwfeels", "$commandlist"]

boards = ["$rule34","$paheal","$dan","$pony"]

### REGEX ###
ey = re.compile( "p[o][n]([e]?)[y]" )
checkEm = re.compile("check.?(th)?(?(1)(em|ese|ose|ine)\\b|(em|my))")

class TwitStreamListener(tweepy.StreamListener):
    def on_status(self, status):
        print('status!')
        try:
            tweet = status.extended_tweet["full_text"]
        except:
            tweet = status.text
        i = 1
        while i == 1:
            if tweet[0]=="@":
                tweet = " ".join(tweet.split()[1:])
            elif tweet[0]!="@":
                i = 0
        tweet = tweet.replace('\n',' / ')
        if "RT @" not in tweet[:4]:
            irc.send("#death",tweet)

def tweetstreamRestart():
    try:
        chibiStream.filter(follow=['1155237236155342848'],is_async=True)
        print("tweet stream timer restarted")
    except:
        print("tweet stream still running.")
    tweetstreamTimer = threading.Timer(1800, tweetstreamRestart)
    tweetstreamTimer.start()

def logsearch(tag, sort, firstlast, caseSens, rawrKame): #sort = 0 for $mention, sort = 1 for $quote
    if rawrKame == "rawr":
        filename = "~/.weechat/logs/rawr.txt"
    elif rawrKame == "kame":
        filename = "~/.weechat/logs/irc.slashnet.#kame-house.weechatlog"
    HTS = "shuf -n 1"
    CS = ""
    if firstlast == 0:
        HTS = "head -1"
    elif firstlast == 1:
        HTS = "tail -1"
    if caseSens == 0:
        CS = "i"
    if sort == 0:
        cmd = 'grep -av{0}E "^.*<\W?{1}.*$" {3} | grep -a{0}E "{1}" | grep -av \\\$ | grep -aiv "chimp\\\s?out" | grep -av "dj-p0n3" | pee "{2}" "wc -l"'.format(
                CS,tag,HTS,filename
                )
    elif sort == 1:
        cmd = 'grep -a{}E "{}.*$" {} | grep -av \\\$ | grep -av "chimp\\\s?out" | grep -aiv "dj-p0n3" | pee "{}" "wc -l"'.format(
                CS,tag,filename,HTS
                )
    print("command: " + cmd)
    greppy = os.popen(cmd).read()
    quote = greppy.split("\n")[0]
    numm = greppy.split("\n")[1]
    return quote, numm

def googlequery(query,searchtype): #searchtype 0 for regular search, 1 for image search
    try:
        resultnum = str(random.randint(1,100))
        if searchtype == 0:
            url = "https://www.googleapis.com/customsearch/v1?&q={}&num=1&key={}&cx={}".format(query, os.environ.get('gapikey'), os.environ.get('cx'))
        elif searchtype == 1:
            url = "https://www.googleapis.com/customsearch/v1?&q={}&searchType=image&start={}&num=1&key={}&cx={}".format(query, resultnum, os.environ.get('gapikey'), os.environ.get('cx'))
        r = requests.get(url, headers=headers)
        json_obj = r.json()
        for search_result in json_obj["items"]:
            return search_result["link"]
    except:
        return "No results found"

def tdProcess(td):
    tdString = str(td)
    if len(str(tdString).split(", ")) > 1:
        daysies = str(tdString).split(", ")[0] + ", "
    else:
        daysies = ""
    fullMins = str(tdString).split(", ")[-1].split(":")
    if (fullMins[0] == '0') and (fullMins[1] == '00'):
        addon = "{} seconds ago".format(fullMins[2])
        if addon[0] == '0':
            addon = addon[1:]
        return addon
    else:
        minnies = fullMins[:2]
        agoString = ''
        if minnies[0] != '0':
            agoString = agoString + "{} hours ".format(minnies[0])
            if agoString == "1 hours ":
                agoString = "1 hour "
        if minnies[1] != '00':
            addon =  "{} minutes".format(minnies[1])
            if addon[0] == '0':
                addon = addon[1:]
            if addon == "1 minutes":
                addon = "1 minute"
            agoString = agoString + addon
        return "{}{} ago".format(daysies, agoString)

def getTimeZone(lat,lon):
    url = 'https://maps.googleapis.com/maps/api/timezone/json?location={},{}&timestamp={}&key={}'
    r = requests.get(url.format(lat,lon,datetime.datetime.now().timestamp(),os.environ.get('gapikey')))
    return r.json()["timeZoneId"]

def geocode(location):
    try:
        place = gn.geocode(location)
        geoLoc = place[0]
        lat = place[1][0]
        lon = place[1][1]
        tZone = getTimeZone(lat, lon)
        return(geoLoc, lat, lon, tZone)
    except Exception as e:
        print(e)
        return 0,0,0,0

def geocodeLocation(weatherLoc, textNick, poneCommand, ud):
    global weatherLocation
    if poneCommand == '':
        location = None
        geoLoc = ''
        for entry in weatherLoc:
            if entry[0] == textNick:
                print(entry)
                location = entry[1]
                geoLoc = entry[2]
                lat = entry[3]
                lon = entry[4]
                tZone = entry[5]
        if (geoLoc == '' or tZone == '') and (location != None):
            geoLoc,lat,lon,tZone = geocode(location)
            ud = True
        elif (location == None) or (geoLoc == 0):
            return 0,0,0,0,0
    else:
        location = str(poneCommand)
        print(location)
        geoLoc,lat,lon,tZone = geocode(location)
        if (geoLoc) == 0:
            return 0,0,0,0,0
    query = ("INSERT INTO locations (nick, location, geoLoc, lat, lon, timezone) "
            "VALUES ('{0}','{1}','{2}','{3}','{4}','{5}') ON DUPLICATE KEY UPDATE "
            "location='{1}',geoLoc='{2}',lat='{3}',lon='{4}', timezone='{5}'".format(
                textNick, 
                location,
                geoLoc,
                lat,
                lon,
                tZone)
            )
    if ud == True:
        weatherLocation = updateLocationSQL(query)
    return geoLoc,lat,lon,query,tZone

def updateLocationSQL(query):
    print("Updating weather SQL...")
    cnxWeather, cursor = openSQL("djpone")
    cursor.execute(query)
    cnxWeather.commit()
    query = "SELECT * FROM locations"
    cursor.execute(query)
    weatherLocation = list(cursor)
    closeSQL(cnxWeather, cursor)
    return weatherLocation

def dubschecker(numb, length):
    i = len(numb)-1
    while length > 0:
        if numb[i] == numb[i-1]:
            i = i-1
            length = length-1
        else:
            break
    if length == 1:
        gisquery = "check my dubs"
        result = googlequery(gisquery,1)
        return result,numb
    else:
        checky = ""
        return checky,numb
        
def garfplug(date,GP):
    if GP == "garf":
        start = datetime.datetime.strptime("06/19/1978", "%m/%d/%Y")
        urlTerm = "http://images.ucomics.com/comics/ga/{}/ga{}{}{}.gif"
    elif GP == "plug":
        start = datetime.datetime.strptime("04/08/2001", "%m/%d/%Y")
        urlTerm = "http://picayune.uclick.com/comics/tmplu/{}/tmplu{}{}{}.gif"
    end = datetime.datetime.now()
    gpDate = start + datetime.timedelta(seconds=random.randint(0,int((end-start).total_seconds())))
    if "/" in date:
        for fmt in ("%m/%d/%y","%m/%d/%Y"):
            try:
                gpDate = datetime.datetime.strptime(date,fmt)
            except:
                pass
    elif "today" in date:
        gpDate = datetime.datetime.now()
    url = urlTerm.format(
        gpDate.strftime("%Y"),gpDate.strftime("%y"),gpDate.strftime("%m"),gpDate.strftime("%d")
        )
    try:
        urlopen(url)
    except HTTPError:
        irc.send (channel, "Comic not found. For best results, input date in MM/DD/YYYY format.")
    else:
        irc.send (channel, url)

def generateHash(fTypeA,fTypeDir):
    N = 5
    fName = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(N))
    if "{}.{}".format(fName, fTypeA) in os.listdir("/mnt/md0/kame-images/public/images/{}".format(fTypeDir)):
        return generateHash(fType)
    else:
        return fName

def allboards(action, poneCommand):
    piclist = []
    Postno = 0
    if action == "$rule34":
        tag = poneCommand.replace(", ","+").replace(" ","_")
        url = "https://rule34.xxx/index.php?page=dapi&q=index&s=post&tags={}".format(tag)
        url2 = "https://rule34.xxx/index.php?page=dapi&q=index&s=post&tags={}&pid={}"
    elif action == "$paheal":
        tag = poneCommand.replace(", ","%20").replace(" ","_")
        url = "https://rule34.paheal.net/post/list/{}/1".format(tag)
    if action == "$rule34":
        try:
            r = requests.get(url, headers = { "User-Agent" : "dj-p0n3/0.4.2 (by zamros on e621)" }, timeout=2)
            root = ET.fromstring(r.text)
            total = int(root.attrib["count"])
            perpage = len(root)
            if total/perpage == 1:
                Pageno = ""
            else:
                Pageno = random.randint(0,math.ceil(total/100)-1)
            url = url2.format(tag,str(Pageno))
            r = requests.get(url, headers={ "User-Agent" : "dj-p0n3/0.4.2 (by zamros on e621)" })
            root = ET.fromstring(r.text)
            perpage = len(root)
            for roo in root:
                piclist.append(roo.attrib["file_url"])
            Postno = random.randint(0,perpage-1)
            Pic = piclist[Postno]
            resultMsg = "{} ({} results)".format(Pic, str(total))
        except Exception as e:
            print(r)
            print(traceback.format_exc())
            piclist = []
            Postno = 0
            resultMsg = "No images found."
    if action == "$paheal":
        try:
            response = urlopen(url)
            soup = BeautifulSoup(response.read(), 'html.parser')
            if action == "$paheal":
                lastList = []
                isOnepage = 1
                for j in soup.find_all("a"):
                    if "Last" in str(j):
                        lastList.append(j.get("href"))
                        isOnepage = 0
                if isOnepage == 0:
                    totalPages = int(lastList[len(lastList)-1].split('/')[len(lastList[len(lastList)-1].split('/'))-1])
                    totalResults = str(totalPages * 70)
                    pahealPage = random.randint(1,totalPages)
                    url = "http://rule34.paheal.net/post/list/{}/{}".format(tag,pahealPage)
                    response = urlopen(url)
                    soup = BeautifulSoup(response.read(),"html.parser")
                for j in soup.find_all("a"):
                    if "File Only" in str(j):
                        piclist.append(j.get("href"))
                if isOnepage == 1:
                    totalResults = str(len(piclist))
                Postno = random.randint(0,len(piclist)-1)
                plural = 's'
                if len(piclist) == 1:
                    plural = ''
                Pic = piclist[Postno]
                resultMsg = "{} ({} result{})".format(Pic, totalResults, plural)
        except Exception as e:
            print(traceback.format_exc())
            piclist = []
            Postno = 0
            resultMsg = "No images found."
    if action == "$dan" or action == "$pony":
        tag = poneCommand.replace(", ","+").replace(" ","_")
        if action == "$dan" and len(tag.split("+")) > 2:
            resultMsg = "Danbooru search can only take a maximum of two terms."
        else:
            if action == "$dan":
                url = "https://danbooru.donmai.us/counts/posts.json?tags={}".format(tag)
                url2 = "https://danbooru.donmai.us/posts.json?api_key="+os.environ.get('danKey')+"&limit=100&login=zamros&page={1}&tags={0}"
                toTerm = ["counts","posts"]
            elif action == "$pony":
                tag = "+%26%26+".join(poneCommand.rsplit(", ")).replace(" ","+")
                url = "https://derpibooru.org/api/v1/json/search/images?q={}&key={}".format(tag, os.environ.get('derpiKey'))
                url2 = "https://derpibooru.org/api/v1/json/search/images?q={0}&page={1}&key="+os.environ.get('derpiKey')
                toTerm = ["total"]
            r = requests.get(url, headers=headers)
            json_obj = r.json()
            try:
                perpage = len(json_obj["search"])
            except:
                try:
                    perpage = len(json_obj["images"])
                except:
                    perpage = 100
            for term in toTerm:
                json_obj = json_obj[term]
            total = json_obj
            if total == 0:
                resultMsg = "No images found."
            else:
                if total>99999 and action == "$dan":
                    Pageno = random.randint(1,1000)
                else:
                    Pageno = random.randint(1,math.ceil(total/perpage))
                url = url2.format(tag, str(Pageno))
                r = requests.get(url, headers=headers)
                json_obj = r.json()
                if action == "$dan":
                    json_obj = json_obj
                elif action == "$pony":
                    json_obj = json_obj["images"]
                for result in json_obj:
                    try:
                        if action == "$dan":
                            piclist.append(result["file_url"])
                        else:
                            piclist.append(result["representations"]["full"])
                    except:
                        pass
                try:
                    Postno = random.randint(0,len(piclist)-1)
                    Pic = piclist[Postno]
                    resultMsg = "{} ({} results)".format(Pic,str(total))
                except:
                    resultMsg = "No images found."
    return resultMsg, piclist, Postno

def openSQL(database):
    cnx = mysql.connector.connect(user=os.environ.get('SQLuser'),password=os.environ.get('SQLkey'),host='localhost',database=database)
    return cnx, cnx.cursor()

def closeSQL(cnx, cursor):
    cursor.close()
    cnx.close()
    
def updateTimerSQL(textNick, alert, channel, tyme, timeset, timerEndstr, kind, timersList):
    cnxTimer, cursor = openSQL("djpone")
    query = ("SELECT MAX(id) AS id FROM timers")
    cursor.execute(query)
    check = [x[0] for x in cursor][0]
    if check == None:
        timerid = 1
    else:
        timerid = check+1
    add_record = ("INSERT INTO timers "
                  "(id, nick, message, channel, duration, timeset, timeend, type) "
                  "VALUES(%s, %s, %s, %s, %s, %s, %s, %s)")
    data_record = (timerid, textNick, alert, channel, tyme, timeset, timerEndstr, kind)
    cursor.execute(add_record, data_record)
    timersList.append(data_record)
    cnxTimer.commit()
    closeSQL(cnxTimer, cursor)
    return timerid, timersList

def isUrlImage(image_url):
    image_formats = ("image/png", "image/jpeg", "image/jpg", "image/gif", "video/webm")
    r = requests.get(image_url)
    try:
        print(r.headers["content-type"])
        if r.headers["content-type"] in image_formats:
            fType = r.headers["content-type"].split('/')[-1]
            if fType == "jpg":
                fType = "jpeg"
            return fType
    except:
        for i in imageTypes:
            if i in image_url[-6]:
                fType = i
    return False

def mySQLwrite(nick, url, urlOrig, msg, vtit, vdesc, tag):
    print("nick: {}\nurl: {}\nurlOrig: {}\nmsg: {}\nvtit: {}\n,vdesc: {}\n,tag: {}\n".format(nick, url, urlOrig, msg, vtit, vdesc, tag))
    desc = "{} :: {} {} :: {} :: {} :: {}".format(nick, urlOrig, msg, vtit, vdesc, int(time.time()))
    cnx, cursor = openSQL("ircman")
    recordTuple = isDupe(urlOrig)
    if len(recordTuple) > 0:
        recordID = recordTuple[0]
        recordRating = recordTuple[2] + 1
        recordVotes = recordTuple[5] + 1
        recordDesc = recordTuple[10] + "\n" + desc
        query = 'UPDATE ircman SET quote="{}", description="{}", votes="{}", rating="{}", timestamp=CURRENT_TIMESTAMP WHERE id={}'.format(
            url,
            recordDesc, 
            recordVotes, 
            recordRating, 
            recordID)
        cursor.execute(query)
    else:
        print("Not a duplicate.")
        query = ("SELECT MAX(id) AS id FROM ircman")
        cursor.execute(query)
        id = int([x[0] for x in cursor][0])+1
        add_record = ("INSERT INTO ircman "
                  "(id, ip, rating, accepted, quote, votes, timestamp, lastLike, lastHate, tags, description, starred) "
                  "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
        data_record = (id, "192.168.1.1",0,1,url,0,datetime.datetime.now(),None,None,tag,desc,None)
        cursor.execute(add_record, data_record)
    cnx.commit()
    closeSQL(cnx, cursor)

def isDupe(url):
    cnx, cursor = openSQL("ircman")
    query = ('SELECT * FROM ircman WHERE description LIKE "%{}%"'.format(url))
    cursor.execute(query)
    try:
        recordTuple = [x for x in cursor][0]
        print("Duplicate found")
        closeSQL(cnx,cursor)
        return recordTuple
    except:
        try:
            query = ('SELECT * FROM ircman WHERE quote LIKE "%{}%"'.format(url))
            cursor.execute(query)
            recordTuple = [x for x in cursor][0]
            closeSQL(cnx, cursor)
            return recordTuple
        except:
            closeSQL(cnx, cursor)
            return []

def trixiUpload(url):
    print("Uploading to trixi...")
    r = requests.get(url)
    fType = isUrlImage(url)
    if fType == False:
        for i in imageTypes:
            if i in url[-6]:
                fType = i
            else:
                fType = "png"
    fName = generateHash(fType, fType)
    if "fjcdn" in url:
        return False
    path = '/mnt/md0/kame-images/public/images/{}/{}.{}'.format(fType, fName, fType)
    with open(path, 'wb') as f:
        f.write(r.content)
    if fType == "png":
        url = "https://i.trixi.cc/{}".format(fName)
    else:
        url = "https://i.trixi.cc/{}/{}".format(fType[0],fName)
    return url, path

def doImage(textNick, url, msg):
    cnx, cursor = openSQL("ircman")
    tag = "resource media image"
    fType = isUrlImage(url)
    urlOrig = url
    recordTuple = isDupe(url)
    if len(recordTuple) > 0:
        url = recordTuple[4]
        urlOrig = recordTuple[-2].split(" :: ")[1]
    if "trixi.cc" in url:
        urlOrig = recordTuple[-2].split(" :: ")[1]
        print("Already on trixi: {} || urlOrig: {}".format(url, urlOrig))
        fName = url.split('/')[-1]
        path = '/mnt/md0/kame-images/public/images/{}/{}.{}'.format(fType, fName, fType)
    else:
        url, path = trixiUpload(url)
        print("Making trixi copy: {}".format(url))
    print(fType)
    if fType == "video/webm":
        tag = "resource media webm"
    closeSQL(cnx, cursor)
    mySQLwrite(textNick, url, urlOrig, msg, "", "", tag)
    return url, path

##TIMER FUNCTIONALITY
def timer(timerid, tyme, name, room, alert,tORr,end):
    if tORr == "t":
        irc.send (room, "{}, {} is up! {}".format(name,tyme,alert))
    elif tORr == "r":
        irc.send (room, "{}, it is now {}! {}".format(name,end,alert))
    cnxTimer, cursor = openSQL("djpone")
    query = "DELETE FROM timers WHERE id={}".format(str(timerid))
    cursor.execute(query)
    cnxTimer.commit()
    closeSQL(cnxTimer, cursor)
    timersList.pop(timersList.index([x for x in timersList if x[0] == timerid][0]))

cnxLoads, cursor = openSQL("djpone")
query = "SELECT * FROM totell"
cursor.execute(query)
tellsList = list(cursor)
query = "SELECT * FROM locations"
cursor.execute(query)
weatherLocation = list(cursor)
if testMode != True:
    query = "SELECT * FROM timers"
    cursor.execute(query)
    timersList = list(cursor)

    for entry in timersList:
        timerid = entry[0]
        name = entry[1]
        mseg = entry[2]
        chan = entry[3]
        tyme = entry[4]
        endT = entry[6]
        tORr = entry[7]
        timeDT = datetime.datetime.strptime(endT, "%Y-%m-%d %H:%M:%S %z")
        timeDiff = timeDT-timenow
        if timeDiff > TD0:
            timerlength = timeDiff.total_seconds()
            t = threading.Timer(timerlength, timer, [timerid,tyme,name,chan,mseg,tORr,endT])
            t.start()
            print("{} {} {} {} {}".format(timeDiff.total_seconds(), tyme, name, chan, mseg))
        else:
            query = "DELETE FROM timers WHERE id = {}".format(timerid)
            cursor.execute(query)
            cnxLoads.commit()
closeSQL(cnxLoads, cursor)

###TWEET STREAM INITIATION###
chibiListener = TwitStreamListener()
chibiStream = tweepy.Stream(auth = api.auth, listener=chibiListener)
tweetstreamTimer = threading.Timer(1800, tweetstreamRestart)
tweetstreamRestart()

###CONNECT TO IRC###
if testMode == False:
    irc.connect(server,channels,os.environ.get('nickname'),os.environ.get('pw'))
else:
    nicky = input("set nick >")
####################MAIN LOOP####################

xxx = True
while xxx == True:
    timenow = central.localize(datetime.datetime.now().replace(microsecond=0))
    try:
        if testMode == True:
            rawText = ":{}!sid93894@16380F9F:C6CF0AF0:41175349:IP PRIVMSG #kame-house :".format(nicky) + input(">")
            rawText = rawText.split("\r\n")
        else:
            rawText = irc.get_text()
            rawText = rawText.split("\r\n")
        rawTextTmp = []
        for text in rawText:
            if "PRIVMSG" in text:
                rawTextTmp.append(text)
        rawText = rawTextTmp
        for text in rawText:
            poneMsg = []
            timenow = central.localize(datetime.datetime.now().replace(microsecond=0))
            #if timenow.strftime("%H:%M") == "12:00":
            #    irc.send("#kame-house","Kobe Bryant is dead.")
            action = ''
            poneCommand = ''
            goodCommand = 0
 
            textNickOrig = text.rsplit("!")[0].lstrip(":")
            textNick = text.rsplit("!")[0].lstrip(":") 

            if textNick[0] == "{":
                textNick = "crank"

            for chan in channels:
                if "PRIVMSG {}".format(chan) in text:
                    channel = chan
            
            print("{} - {}".format(timenow.strftime("%m/%d/%y %H:%M:%S"),text))
            
            if ("Mir4g3" in text) and ("JOIN :#death" in text):
                irc.send("#death","I come inreturn to the beginning of the end to the beggin the journey of souls the god head universal for whow the is no death, only Live Eternal")

            if ":$" in text or (channel == "#titties" and ":!" in text):
                print("found command")
                print(channel)
                for command in poneCommands:
                    if command in text:
                        action = command
                        try:
                            poneCommand = text.split(":{} ".format(command))[1]
                            print("A command! {} - {}".format(action, poneCommand))
                            goodCommand = 1
                            break
                        except:
                            if command in flexCommands:
                                poneCommand = ''
                                break
                            elif command in noInput:
                                poneCommand = ''
                                goodCommand = 1
                                break
                            else:
                                poneMsg.append("Please enter a query.")
                                break

            tellsListTemp = [x for x in tellsList]
            for tell in tellsListTemp:
                if tell[1].lower() == textNick.lower():
                    try:
                        td = timenow-central.localize(tell[4])
                        print("Had to localize")
                    except Exception as e:
                        td = timenow-tell[4]
                        print("Already localized")
                        print(Exception)
                    agoString = tdProcess(td)
                    print("sending {} to {}".format(tell[2],textNickOrig))
                    irc.send(textNickOrig, "{} said: {} ({})".format(
                        tell[2],
                        tell[3],
                        agoString
                        )
                    )
                    tellsList.pop(tellsList.index(tell))
                    cnxTell, cursor = openSQL("djpone")
                    query = "DELETE FROM totell WHERE id = {}".format(tell[0])
                    cursor.execute(query)
                    cnxTell.commit()
                    closeSQL(cnxTell, cursor)

            if ("http" in text.lower()) and ("dj-p0n3" not in text.lower()) and (action != "$tweet"):
                print('found url')
                for word in text.split():
                    if "twitter.com/" in word.lower():
                        url = word.lstrip(":")
                        tweetID = url.split("status/")[-1].split("/")[0].split("?")[0]
                        tag = "resource media tweet"
                        msg = text.split("{} :".format(channel))[-1].split("{} ".format(url))[-1].split(" http")[0].lstrip(":")
                        if msg == url:
                            msg = ""
                        url2 = "https://api.twitter.com/2/tweets?ids={}&expansions=author_id".format(tweetID)
                        response = requests.get(url2, headers=tweetHeaders)
                        json_obj = response.json()
                        tweeText = json_obj["data"][0]["text"].replace("\n"," / ")
                        tweeUser = json_obj["includes"]["users"][0]["name"]
                        print("{} - {}".format(tweeText,tweeUser))
                        poneMsg.append("{} on Twitter - {}".format(tweeUser,tweeText))
                        url = url.split(tweetID)[0]+tweetID
                        mySQLwrite(textNick, url, url, msg, "", "", tag)
                    elif "youtu" in word.lower():
                        if ("cq1g8czIBJY" in word or "d2lJUOv0hLA" in word):
                            poneMsg.append("Fuck you.")
                        else:
                            print(word)
                            tag = "resource media video"
                            url = word.lstrip(":")
                            msg = text.split("{} :".format(channel))[-1].split("{} ".format(url))[-1].split(" http")[0].lstrip(":")
                            if msg == url:
                                msg = ""
                            vidID = url.split('/')[-1].split('=')[-1]
                            print(vidID)
                            url2 = "https://youtube.googleapis.com/youtube/v3/videos?part=snippet&id={}&key={}".format(vidID,os.environ.get('gapikey'))
                            print(url)
                            response = requests.get(url2)
                            print(response)
                            json_obj = response.json()
                            vidTitle = json_obj["items"][0]["snippet"]["title"]
                            vidDesc = json_obj["items"][0]["snippet"]["description"].split("\n")[0]
                            vidUplo = json_obj["items"][0]["snippet"]["channelTitle"]
                            poneMsg.append("{} - {} - uploaded by {}".format(vidTitle,vidDesc,vidUplo))
                            mySQLwrite(textNick, url, url, msg, vidTitle, vidDesc, tag)
                    elif ("http" in word) and (isUrlImage(word.lstrip(":"))):
                        tag = "resource media image"
                        url = word.lstrip(":")
                        msg = text.split("{} :".format(channel))[-1].split("{} ".format(url))[-1].split(" http")[0].lstrip(":")
                        if msg == url:
                            msg = ""
                        if "trixi" in word:
                            urlOrig = url
                            if "/w/" in word:
                                tag = "resource media webm"
                            mySQLwrite(textNick, url, urlOrig, msg, "", "", tag)
                        else:
                            doImage(textNick, url, msg)
                    elif "http" in word and "zip" not in word and "rar" not in word and "webcam" not in word:
                        pageTitle = "No title"
                        pageDescr = "No description"
                        tagge = "resource link"
                        url = word.lstrip(":")
                        print(url)
                        r = requests.get(url, headers=headers, timeout=2)
                        soup = BeautifulSoup(r.text, 'html.parser')
                        meta = soup.find_all("meta")
                        for tag in meta:
                            if "property" in tag.attrs.keys() and tag.attrs["property"].strip().lower() == "og:title":
                                pageTitle = tag.attrs['content']
                            elif "name" in tag.attrs.keys() and tag.attrs["name"].strip().lower() == "title":
                                pageTitle = tag.attrs['content']
                            elif "property" in tag.attrs.keys() and tag.attrs["property"].strip().lower() == "og:description":
                                pageDescr = tag.attrs['content']
                            elif "name" in tag.attrs.keys() and tag.attrs["name"].strip().lower() == "description":
                                pageDescr = tag.attrs['content']
                        if pageTitle == "No title" and pageDescr == "No description":
                            sendString = ""
                        elif pageTitle == "No title":
                            sendString = pageDescr
                        elif pageDescr == "No description":
                            sendString = pageTitle
                        else:
                            sendString = "{} - {}".format(pageTitle,pageDescr)
                        poneMsg.append(sendString)
                        mySQLwrite(textNick, url, url, sendString, "", "", tagge)
                    else:
                        pass

            if "prices" in text.lower():
                symbol = text.split("prices")[-2].split(":")[-1].split(" ")[-2]
                url = "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={}&apikey={}".format(symbol,os.environ.get('stockAPIkey'))
                r = requests.get(url)
                json_obj = r.json()
                gloQuo = json_obj["Global Quote"]
                if gloQuo == {}:
                    poneMsg.append("Prices not found.")
                else:
                    symb = gloQuo["01. symbol"]
                    price = gloQuo["05. price"]
                    change = gloQuo["10. change percent"]
                    poneMsg.append("{}: {} ({})".format(symb, price, change))

##STOCK PHOTOS
            if action == "$stock" and goodCommand == 1:
                try:
                    tagdata = poneCommand.replace(" ","+")
                    url = "https://www.shutterstock.com/search/" + tagdata
                    r = requests.get(url, headers=headers)
                    soup = BeautifulSoup(r.text, "html.parser")
                    images = soup.find_all("img")
                    resultList = []
                    for image in images:
                        if image.get("src") == None:
                            print(image.get("src"))
                        else:
                            resultList.append(image)
                    resultnum = random.randint(0, len(resultList))
                    poneMsg.append("{} - {} ({} results)".format(
                        resultList[resultnum].get("src"),
                        resultList[resultnum].get("alt"),
                        soup.find("h2").text.split()[0]
                        )
                    )
                except:
                    poneMsg.append("No images found.")


#            if action == "$aqi":
#                place, query = geocodeLocation(weatherLocation, textNick, poneCommand)
#                if place != 0:
#                    weatherLocation = updateLocationSQL(query)
#                    url = "http://api.airvisual.com/v2/nearest_city?lat={}&lon={}&key={}".format(place[0],place[1],os.environ.get('aqiKey'))
#                    r = requests.get(url)
#                    json_obj = r.json()
#                    aqi = json_obj["data"]["current"]["pollution"]["aqius"]
#                    if aqi <= 50:
#                        cStr = "\x0303"
#                        term = "Good"
#                    elif 50<aqi<101:
#                        cStr = "\x0308"
#                        term = "Moderate"
#                    elif 100<aqi<151:
#                        cStr = "\x0304"
#                        term = "Unhealthy for Sensitive Groups"
#                    elif 150<aqi<201:
#                        cStr = "\x0305"
#                        term = "Unhealthy"
#                    elif 200<aqi<301:
#                        cStr = "\x0306!! "
#                        term = "Very Unhealthy !!"
#                    elif aqi>300:
#                        cStr = "\x0313!! "
#                        term = "Hazardous !!"
#                    irc.send(channel,"{} - AQI: {}{} - {}".format(place, cStr, str(aqi), term))
#                else:
#                    irc.send(channel,"Error retrieving air quality.")

##WEATHER
            if action == "$we":
                if poneCommand.split(" ")[0] == "set":
                    udWeather = True
                else:
                    udWeather = False
                place,lat,lon,query,tZone = geocodeLocation(weatherLocation, textNick, poneCommand.split("set ")[len(poneCommand.split("set "))-1], udWeather)
                print(place)
                if place != 0:
                    try:
                        url = "https://api.darksky.net/forecast/a374bb1ecd2787c709432380730cad22/{},{}".format(lat,lon)
                        r = requests.get(url)
                        json_obj = r.json()
                        todayDay = time.strftime("%m/%d/%y", time.gmtime(json_obj["currently"]["time"]))
                        todaySummary = json_obj["daily"]["data"][0]["summary"]
                        tempF = str(json_obj["currently"]["temperature"])
                        tempC = str(round(((json_obj["currently"]["temperature"])-32)*(5/9),2))
                        humidity = str(round(json_obj["currently"]["humidity"]*100,2)) + "%"
                        precipProb = str(round(json_obj["currently"]["precipProbability"]*100,2)) + "%"
                        windSpeedMPH = str(json_obj["currently"]["windSpeed"]) + " MPH"
                        windspeedKPH = str(round((json_obj["currently"]["windSpeed"]*1.60934),2)) + " Km/H"
                        tomorrowDay = time.strftime("%m/%d/%y", time.gmtime(json_obj["daily"]["data"][1]["time"]))
                        tomorrowSummary = json_obj["daily"]["data"][1]["summary"]
                        tomorrowHighF = str(json_obj["daily"]["data"][1]["temperatureHigh"])
                        tomorrowLowF = str(json_obj["daily"]["data"][1]["temperatureLow"])
                        tomorrowHighC = str(round(((json_obj["daily"]["data"][1]["temperatureHigh"])-32)*(5/9),2))
                        tomorrowLowC = str(round(((json_obj["daily"]["data"][1]["temperatureLow"])-32)*(5/9),2))
                        tomorrowHumid = str(round(json_obj["daily"]["data"][1]["humidity"]*100,2)) + "%"
                        tomorrowprecipProb = str(round(json_obj["daily"]["data"][1]["precipProbability"]*100,2)) + "%"
                        poneMsg.append(
                                    "{} {}: {} {}\xb0F ({}\xb0C), Humidity {}, {} chance of precipitation. Wind speed {} ({}). Tomorrow {} - {} High {}\xb0F ({}\xb0C), Low {}\xb0F ({}\xb0C), Humidity {}, {} chance of precipitation.".format(
                                    place, 
                                    todayDay, 
                                    todaySummary, 
                                    tempF, 
                                    tempC, 
                                    humidity, 
                                    precipProb, 
                                    windSpeedMPH, 
                                    windspeedKPH, 
                                    tomorrowDay, 
                                    tomorrowSummary, 
                                    tomorrowHighF, 
                                    tomorrowHighC, 
                                    tomorrowLowF, 
                                    tomorrowLowC, 
                                    tomorrowHumid, 
                                    tomorrowprecipProb
                                    )
                            )
                    except:
                        poneMsg.append("Error retrieving weather.")
                else:
                    poneMsg.append("Looks like you don't have a location set! Use $we set [location].")

            if action == "$garf":
                garfplug(poneCommand,"garf")
            
            if action == "$pluggers":
                garfplug(poneCommand,"plug")
            
            if action == "$wiki":
                randUrl = "https://en.wikipedia.org/wiki/Special:Random"
                endUrl = 'https://en.wikipedia.org/w/api.php?format=json&action=query&prop=extracts&explaintext=1&formatversion=2&titles={}'
                randResponse = urlopen(randUrl)
                soup = BeautifulSoup(randResponse.read(), 'html.parser')
                pageName = soup.title.string[:-12].replace(" ","_")
                r = requests.get(endUrl.format(pageName))
                json_obj = r.json()
                linkUrl = "https://en.wikipedia.org/wiki/{}".format(soup.title.string[:-12].replace(" ","_"))
                print(linkUrl)
                g = tokenize.sent_tokenize(json_obj["query"]["pages"][0]["extract"])
                j = random.choice(g)
                stop = False
                while stop == False:
                    if "=" in j:
                        print("header")
                        j = random.choice(g)
                    else:
                        stop = True
                poneMsg.append(j)

            if action == "$page":
                try:
                    poneMsg.append(linkUrl)
                except:
                    pass

            if action == "$legalweed":
                d = {}
                with open("states.txt") as f:
                    for line in f:
                        splat = line.split()
                        if len(splat) == 3:
                            splat[0:2] = [" ".join(splat[0:2])]
                        (key, val) = splat
                        d[key] = val
                url = "https://en.wikipedia.org/w/api.php?format=json&action=query&titles=Template:Cannabis_in_the_United_States&prop=revisions&rvprop=content"
                r = requests.get(url)
                json_obj = r.json()
                page = str(json_obj).split("group2")
                sta = []
                for key in d:
                    if key in page[2]:
                        sta.append(d[key])
                sta.sort()
                states = ", ".join(sta)
                poneMsg.append("There are {} states with legalized recreational marijuana: {}".format(str(len(sta)),states))

            if action == "$rand":
                N = random.randint(419, 421) 
                if N == 420:
                    poneMsg.append("\x0303" + str(N))
                else:
                    poneMsg.append(str(N))

            if "flips table" in text:
                poneMsg.append("(╯°□°）╯︵ ┻━┻")

###DUBS TRIPS QUADS CHECK EM
            if "dubs" in text.lower() or "doubles" in text.lower() or "dubz" in text.lower():
                checked,numb = dubschecker(str(int(time.time())), 2)
                poneMsg.append(numb + " " + checked)
            elif "trips" in text.lower() or "triples" in text.lower():
                checked,numb = dubschecker(str(int(time.time())), 3)
                poneMsg.append(numb + " " + checked)
            elif 'quads' in text.lower() or "quadruples" in text.lower():
                checked,numb = dubschecker(str(int(time.time())), 4)
                poneMsg.append(numb + " " + checked)
            elif checkEm.findall(text.lower()):
                checked,numb = dubschecker(str(int(time.time())), 2)
                poneMsg.append(numb + " " + checked)
             
            if action == "$urwfeels":
                poneMsg.append(random.choice(open("urwfeels.txt").read().splitlines()))

##TIMER FUNCTIONALITY
            if action == "$timer" and goodCommand == 1:
                tORr = "t"
                tyme = poneCommand.split()[0]
                alert = " ".join(poneCommand.split()[1:])
                timerlength = irc.timecruncher(tyme)
                if timerlength == 0:
                    poneMsg.append("Unrecognized length of time. Please use s, m, h, d, w, y")
                else:
                    timerEnd = timenow+datetime.timedelta(seconds=timerlength)
                    timerEndstr = timerEnd.strftime("%Y-%m-%d %H:%M:%S %z")
                    timerid, timersList = updateTimerSQL(textNick, alert, channel, tyme, timenow.strftime("%Y-%m-%d %H:%M:%S"), timerEndstr, tORr, timersList)
                    t = threading.Timer(timerlength, timer, [timerid,tyme,textNick,channel,alert,tORr,timerEndstr])
                    t.start()
                    poneMsg.append("{}: Timer set.".format(textNick))
                    print("Timer set for {} from now.".format(str(timerlength)))

            if action == "$timeleft":
                if poneCommand == "":
                    numTimers = 1
                else:
                    try:
                        numTimers = int(poneCommand.split()[0])
                        if numTimers<1:
                            numTimers = 1
                    except:
                        numtimers = 1
                timeremindList = []
                for timar in timersList:
                    if timar[1] == textNick:
                        timeremindList.append((timar, datetime.datetime.strptime(timar[6], "%Y-%m-%d %H:%M:%S %z")-timenow))
                if len(timeremindList) == 0:
                    poneMsg.append("{}, you have no timers set.".format(textNick))
                elif len(timeremindList) > 1:
                    timeremindList = timeremindList[-numTimers:]
                for timar in timeremindList:
                    print(timar)
                    if timar[0][7] == "t":
                        duration = timar[0][4]
                        remindString = "{}, your {} timer for '{}' will be up in {}"
                    else:
                        duration = timar[0][6]
                        remindString = "{}, your timer set to go off at {} for '{}' will be up in {}"
                    poneMsg.append(remindString.format(
                        textNick,
                        duration,
                        timar[0][2],
                        str(timar[1])
                        )
                    )

            if action == "$remind" and goodCommand == 1:
                tORr = "r"
                success = False
                remindEnd = ""
                tZone = ""
                for entry in weatherLocation:
                    if entry[0].lower() == textNick.lower():
                        print(entry)
                        tZone = entry[5]
                        if tZone == "":
                            _,_,_,_,tZone = geocodeLocation(weatherLocation, textNick, '', '')
                print(tZone)
                if tZone == "":
                    poneMsg.append("Looks like you don't have a time zone set! Use $we set [location].")
                else:
                    splitlist = poneCommand.split(" ")
                    for s in reversed(range(1,4)):
                        for Date in fmtsDate:
                            for Time in fmtsTime:
                                for Order in fmtsOrderz:
                                    if success == True:
                                        break
                                    fmt = Order.format(Date,Time)
                                    try:
                                        remindEnd = datetime.datetime.strptime(" ".join(splitlist[:s]), fmt)
                                        if (remindEnd.year == 1900) and (remindEnd.month == 1) and (remindEnd.day == 1):
                                            remindEnd = remindEnd.replace(year=timenow.year,day=timenow.day,month=timenow.month)
                                        elif (remindEnd.year == 1900):
                                            remindEnd = remindEnd.replace(year=timenow.year)
                                        success = True
                                        alert = " ".join(splitlist[s:])
                                        break
                                    except Exception as e:
                                        pass
                    if remindEnd == "":
                        poneMsg.append("Unrecognized length of time. For best results, use M/D/Y H:M format!")
                    else:
                        print(remindEnd)
                        TZ = pytz.timezone(tZone)
                        remindEnd = TZ.localize(remindEnd)
                        remindStart = timenow
                        remindlength = remindEnd-remindStart
                        if remindlength < TD0:
                            poneMsg.append("You're trying to set a reminder for the past... we all wish we could go back...")
                        else:
                            remindlength = remindlength.total_seconds()
                            print("remindEnd: {}\nremindStart: {}\nremindLength: {}".format(remindEnd,remindStart,remindlength))
                            tyme = str(remindlength)
                            remindEndstr = remindEnd.strftime("%Y-%m-%d %H:%M:%S %z")
                            timerid, timersList = updateTimerSQL(textNick, alert, channel, tyme, timenow.strftime("%Y-%m-%d %H:%M:%S"), remindEndstr, "r", timersList)
                            t = threading.Timer(remindlength, timer, [timerid,tyme,textNick,channel,alert,tORr,remindEndstr])
                            t.start()
                            poneMsg.append("{}: Timer set for {}".format(textNick,remindEnd.strftime("%m/%d/%y %H:%M:%S %Z")))
###TELLING ###
            if action == "$tell" and goodCommand == 1:
                if "$tell dj-p0n3" in text.lower():
                    poneMsg.append("I'm right here. Say it to my face, motherfucker.")
                else:
                    toNick = poneCommand.split()[0]
                    if toNick[0] == "{":
                        toNick = "crank"
                    tellMsg = " ".join(poneCommand.split()[1:])
                    tellTime = timenow.strftime("%Y-%m-%d %H:%M:%S")
                    add_record = ("INSERT INTO totell " "(id, nick, fromNick, message, time) " "VALUES(%s, %s, %s, %s, %s)")
                    cnxTell, cursor = openSQL("djpone")
                    query = ("SELECT MAX(id) AS id FROM totell")
                    cursor.execute(query)
                    check = [x[0] for x in cursor][0]
                    if check == None:
                        tellid = 1
                    else:
                        tellid = check+1
                    newTell = (tellid, toNick, textNick, tellMsg, tellTime)
                    tellsList.append((tellid, toNick, textNick, tellMsg, timenow))
                    cursor.execute(add_record, newTell)
                    cnxTell.commit()
                    closeSQL(cnxTell, cursor)
                    confirmations = ["Okey Dokey Lokey! :3c",
                                    "::m voice:: I'll pass that along.",
                                    "Sure thing, boss.",
                                    "Why would you tell someone that?",
                                    "Alright. But there's no way to take this back.",
                                    "Interesting message....",
                                    "Is that really necessary?",
                                    "Oh my god, I love MLP too!"]
                    poneMsg.append("{}: {}".format(
                        textNick,
                        random.choice(confirmations)
                       )
                    )
            
            if action == "$paheal" and goodCommand == 1:
                result, piclist, Postno = allboards(action,poneCommand)
                print(result)
                poneMsg.append(result)

###CHOICES###
            if action == "$choose" and goodCommand == 1:
                poneMsg.append("{}: {}".format(textNick,random.choice(poneCommand.split(", "))))
###LOG SEARCH ###
            for splitter in poneCommands[:12]:
                if action == splitter and goodCommand == 1:
                    tag = poneCommand.split()
                    if tag[0] == "rawr":
                        tag = tag[1:]
                        rawrKame = "rawr"
                    else:
                        rawrKame = "kame"
                    if tag[0] == "-r":
                        tag = tag[1:]
                        if tag[0] == "rawr":
                            rawrKame = "rawr"
                            tag = tag[1:]
                        else:
                            rawrKame = "kame"
                    else:
                        i=0
                        while i<len(tag):
                            for x in grepEscape:
                                if x in tag[i]:
                                    tag[i] = tag[i].replace(x,"\\"+x)
                            i+=1
                    sort = 0
                    caseSens = 0
                    firstlast = 99
                    if "quote" in splitter or "Quote" in splitter:
                        print("Quote")
                        tag = "{}.*{}".format("^.*<\W?{}>".format(tag[0])," ".join(tag[1:]))
                        print("Tag: {}".format(tag))
                        sort = 1
                    elif "mention" in splitter or "Mention" in splitter:
                        tag = " ".join(tag)
                        print("Mention")
                        print("Tag: {}".format(tag))
                    if "first" in splitter:
                        firstlast = 0
                    elif "last" in splitter:
                        firstlast = 1
                    if "Mention" in splitter or "Quote" in splitter:
                        caseSens = 1
                        print("Case sensitive, caseSens = 1")
                    grepResult, num = logsearch(tag,sort,firstlast,caseSens,rawrKame)
                    print(grepResult)
                    poneMsg.append("{} {{{}}}".format(grepResult, num))
                    break

            if action == "$explain":
                try:
                    for x in grepEscape:
                        if x in grepResult:
                            grepResult = grepResult.replace(x,'\\'+x)
                    print(grepResult)
                    if rawrKame == "rawr":
                        filename = "~/.weechat/logs/rawr.txt"
                    else:
                        filename = "~/.weechat/logs/irc.slashnet.#kame-house.weechatlog"
                    cmd = 'grep -aUE -m1 -B 20 -A 50 "{}" {} > /mnt/md0/trixi/explain.txt'.format(
                        grepResult, filename
                        )
                    print(cmd)
                    os.popen(cmd).read()
                    poneMsg.append("Explanation at https://trixi.cc/explain.txt")
                except:
                    poneMsg.append("No log search to explain.")
            
            if "PRIVMSG" in text and os.environ.get('nickname') in text and "facemaker" in text:
                irc.quit()
                xxx = False

            if "PRIVMSG" in text and "tweet restart" in text:
                try:
                    tweetstreamRestart()
                except:
                    print("Tweet stream still running.")

            if action == "$fun milo":
                poneMsg.append('ahhh milo wot a good idea' )
                poneMsg.append('\x01ACTION decides hot milo made with milk and marshmellows sounds great\x01' )
                poneMsg.append('OK who wants one?????' )
                poneMsg.append('aren\'t ya glad you have a clever bot ;)' )   

            if action == "$bogpill":
                poneMsg.append(random.choice(open('quickrundown.txt').read().splitlines()))

            if action == "$honk":
                if poneCommand == "":
                    i = 1
                else:
                    i = int(poneCommand)
                    if i > 5:
                        i = 5
                j = 0
                while j < i:
                    imgurName = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(5))
                    imgUrl = "https://i.imgur.com/{}.png".format(imgurName)
                    r = requests.get(imgUrl, allow_redirects = False)
                    keepGoing = 1
                    while keepGoing == 1:
                        if r.status_code == 302:
                            print('No good: ' + imgUrl)
                            imgurName = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(5))
                            imgUrl = "https://i.imgur.com/{}.png".format(imgurName)
                            r = requests.get(imgUrl, allow_redirects = False)
                        elif r.status_code == 200:
                            #irc.send (channel, imgUrl)
                            poneMsg.append(imgUrl)
                            j+=1
                            keepGoing = 0
                        
            if action == "$yt" and goodCommand == 1:
                if "sumer" in poneCommand.lower():
                    poneMsg.append("Fuck you")
                else:
                    #add youtube v3 api key
                    ytapikey = os.environ.get('ytapikey')
                    try:
                        r = requests.get("https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=1&type=video&q={}&key={}".format(poneCommand, ytapikey))
                        search_response = r.json()
                        for search_result in search_response["items"]:
                            vidURL = "https://www.youtube.com/watch?v={}".format(search_result["id"]["videoId"])
                            vidTitle = search_result["snippet"]["title"]
                            vidDesc = search_result["snippet"]["description"]
                            poneMsg.append("{} - {} - {}".format(
                                vidURL, vidTitle, vidDesc
                                )
                            )
                    except Exception as e:
                        print(e)
                        poneMsg.append("No results found.")
                    mySQLwrite(textNick,vidURL,vidURL,"($yt {})".format(poneCommand),vidTitle,vidDesc,"resource media video")

            if action == "$bible":
                if poneCommand == "":
                    url = "http://labs.bible.org/api/?passage=random&type=json"
                    r = requests.get(url,headers)
                    try:
                        json_obj = r.json()
                        poneMsg.append(
                            "{} {}:{} - {}".format(
                            str(json_obj[0]["bookname"]),
                            str(json_obj[0]["chapter"]),
                            str(json_obj[0]["verse"]),
                            str(json_obj[0]["text"])
                            )
                        )
                    except:
                        poneMsg.append('Verse not found.')
                else:
                    url = "https://bible-api.com/{}?translation=kjv".format(quote(''.join(poneCommand)))
                    r = requests.get(url,headers)
                    json_obj = r.json()
                    try:
                        poneMsg.append(
                            "{} - {}".format(
                            str(json_obj['reference']), 
                            str(json_obj['text']).replace('\n',' ')
                            )
                        )
                    except:
                        poneMsg.append("Verse not found.")

            if action == "$koran":
                if poneCommand == "":
                    ayah = str(random.randint(1,6236))
                else:
                    ayah = poneCommand.split()[0]
                url = 'http://api.alquran.cloud/v1/ayah/{}/{}'.format(ayah,'en.yusufali')
                r = requests.get(url)
                json_obj = r.json()
                if json_obj["code"] == 200:
                    ayahResult = json_obj["data"]
                    ayah = ayahResult["number"]
                    poneMsg.append("{} - {}".format(
                        str(ayah),
                        ayahResult["text"])
                        )
                else:
                    poneMsg.append("Verse not found.")

            if action == "$korannext":
                try:
                    ayah += 1
                    url = "http://api.alquran.cloud/v1/ayah/{}/{}".format(ayah,"en.yusufali")
                    r = requests.get(url)
                    json_obj = r.json()
                    if json_obj["code"] == 200:
                        ayahResult = json_obj["data"]
                        ayah = ayahResult["number"]
                        poneMsg.append("{} - {}".format(
                            str(ayah),
                            ayahResult["text"])
                            )
                    else:
                        poneMsg.append("Verse not found.")
                except:
                    poneMsg.append("There have been no recent Koran searches.")

            if action == "$tv_next" or action == "$tv_last" and goodCommand == 1:
                show = quote(poneCommand)
                if "next" in action:
                    url = "http://api.tvmaze.com/singlesearch/shows?q={}&embed=nextepisode".format(show)
                    flag = "nextepisode"
                    intro = "The next scheduled episode of "
                    transition = " - "
                elif "last" in action:
                    url = "http://api.tvmaze.com/singlesearch/shows?q={}&embed=previousepisode".format(show)
                    flag = "previousepisode"
                    intro = "The last episode of "
                    transition = " aired "
                try:
                    r = requests.get(url)
                    json_obj = r.json()
                    if json_obj == "null":
                        poneMsg.append("Show not found.")
                    elif json_obj == {}:
                        poneMsg.append("Show not found.")
                    elif "_embedded" not in json_obj:
                        poneMsg.append("There are no scheduled upcoming episodes of {}".format(json_obj["name"]))
                    else:
                        poneMsg.append (
                                "{}{}{}{} - S{}E{} - {}".format(
                                intro, json_obj["name"], 
                                transition, 
                                json_obj["_embedded"][flag]["airdate"],
                                str(json_obj["_embedded"][flag]["season"]),
                                str(json_obj["_embedded"][flag]["number"]), 
                                json_obj["_embedded"][flag]["name"]
                                )
                            )
                except:
                    poneMsg.append("Show not found.")

            if action == "$gis" and goodCommand == 1:
                result = googlequery(poneCommand,1)
                print(result)
                doImage(textNick, result, "($gis {})".format(poneCommand))
                poneMsg.append(result)

            if action == "$g" and goodCommand == 1:
                poneCommand2 = poneCommand + " -site:youtube.com"
                result = googlequery(poneCommand2,0)
                poneMsg.append(result)
                mySQLwrite(textNick, result, result, "($g {})".format(poneCommand), "", "", "resource link")

            if action == "$adom" and goodCommand == 1:
                gquery = "adom wiki {}".format(poneCommand)
                result = googlequery(gquery,0)
                poneMsg.append(result)
           
            if action == "$rule34" and goodCommand == 1:
                result, piclist, Postno = allboards(action,poneCommand)
                poneMsg.append(result)

            if action == "$dan":
                result, piclist, Postno = allboards(action,poneCommand)
                poneMsg.append(result)

            if action == "$hey":
                url = "https://www.reddit.com/r/{}.json".format(poneCommand)
                r = requests.get(url, headers=headers)
                try:
                    json_obj = r.json()
                    children = json_obj["data"]["children"]
                    test = children[0]["data"]
                except:
                    children = []
                if len(children) == 0:
                    poneMsg.append("Invalid (or empty) subreddit.")
                elif len(children) > 0:
                    n = random.randint(0, (len(children))-1)
                    print(n)
                    if len(children) > 1:
                        while "stickied" in children[n]["data"] and children[n]["data"]["stickied"] == True:
                            n += 1
                    print(n)
                    if "submit_text_html" in children[n]["data"]:
                        poneMsg.append("Invalid (or empty) subreddit.")
                    else:
                        post = children[n]["data"]
                        if "self." in post["domain"]:
                            permalink = post["selftext"][:120]+"..."
                        else:
                            permalink = "http://www.reddit.com{}".format(post["permalink"])
                        poneMsg.append (
                            "{} ({}) - {} - {}".format(
                            str(post["title"]), 
                            str(post["domain"]),
                            str(post["url"]), 
                            permalink
                                )
                            )
            
            if action == "$sup":
                url = "https://a.4cdn.org/{}/1.json".format(poneCommand.strip('/'))
                r = requests.get(url)
                fourChan = r.json()
                thread = random.choice(fourChan["threads"])
                print(thread)
                if "sub" in thread["posts"][0]:
                    title = "{} | ".format(html.unescape(thread["posts"][0]["sub"]))
                else:
                    title = ""
                if "com" in thread["posts"][0]:
                    text = html.unescape(thread["posts"][0]["com"][:250])
                    text = "{} | ".format(re.sub(cleanr, '', text.replace("<br>"," / ")))
                else:
                    text = ""
                link = "https://boards.4chan.org/{}/thread/{}".format(
                    poneCommand.strip("/"),
                    thread["posts"][0]["no"]
                    )
                try:
                    filename = str(thread['posts'][0]['tim']) + thread['posts'][0]['ext']
                    print(filename)
                    imageurl = "https://i.4cdn.org/{}/{}".format(
                        poneCommand.strip("/"),
                        filename
                        )
                    #local = "/mnt/md0/trixi/4ch/{}".format(filename)
                    #urlretrieve(imageurl, local)
                    #imglink = "https://trixi.cc/4ch/{} - ".format(filename)
                    imglink, _ = doImage("dj-p0n3", imageurl, '')
                except Exception as e:
                    imglink = "No image - "
                    print("No image")
                    print(e)
                poneMsg.append("{}{}{}{}".format(
                    imglink,
                    title,
                    text,
                    link
                    ))

            if action == "$pony" and goodCommand == 1:
                result, piclist, Postno = allboards(action,poneCommand)
                print(result)
                poneMsg.append(result)

            if action == "$ponyall" and goodCommand == 1:
                tag = "+%26%26+".join(text.rpartition("$ponyall ")[2].rsplit(", ")).replace(" ","+")
                url = "https://trixiebooru.org/search?q=" + tag
                poneMsg.append(url)

            if action == "$help":
                helplist = ["https://kame.us/help.mp4","https://p.ancak.es/help.mp4","https://trixi.cc/help.mp4"]
                poneMsg.append(random.choice(helplist))

            if action == "$tweet" and channel == "#kame-house":
                nope = False
                if "@" in poneCommand:
                    for word in forbiddenTweets:
                        if len(re.compile(r"\b{}\b".format(word)).findall(poneCommand.lower())) > 0:
                            nope = True
                if nope == True:
                    poneMsg.append("You are a bad person.")
                else:
                    try:
                        medias = []
                        tweetID = ""
                        kwargDict = {}
                        if ("http" in poneCommand): #and (isUrlImage([word for word in poneCommand.split() if "http" in word][0])):
                            urls = [word for word in poneCommand.split() if "http" in word]
                            medias = []
                            for addy in urls:
                                print(addy)
                                if isUrlImage(addy) != False:
                                    poneCommand = (poneCommand.split(addy)[0]+poneCommand.split(addy)[-1].lstrip(" ")).rstrip(" ")
                                    _, path = doImage(textNick, addy, '')
                                    medias.append(api.media_upload(path).media_id_string)
                        if ("/status/" in poneCommand) and (poneCommand.split()[0].lower() != "quote"):
                            tweetID = poneCommand.split("/status/")[-1].split()[0]
                            for word in poneCommand.split():
                                if "twitter.com/" in word:
                                    poneCommand = (poneCommand.split(word)[0]+poneCommand.split(word)[-1].lstrip(" ")).rstrip(" ")
                        elif ("/status/" in poneCommand) and (poneCommand.split()[0].lower() == "quote"):
                            poneCommand = poneCommand[6:]
                        if tweetID != "":
                            kwargDict["in_reply_to_status_id"] = tweetID
                            kwargDict["auto_populate_reply_metadata"] = True
                        if medias != []:
                            kwargDict["media_ids"] = medias
                        kwargDict["status"] = poneCommand
                        status= api.update_status(**kwargDict)
                        poneMsg.append("Tweeted! https://twitter.com/jerwill64/status/{}".format(status.id_str))
                    except Exception as e:
                        poneMsg.append("Error tweeting - {}".format(e))

            if action == "$commandlist":
                poneMsg.append("($first, $last) {}, {}".format(", ".join(poneCommands[0:2]), ", ".join(poneCommands[12:47])))

            if channel + " :!crankowned" in text:
                poneMsg.append("\x0304YES, Crank is currently owned, he will forever be owned for all eternity.")

            if "james" in text:
                poneMsg.append("dorito")

            if ey.findall(text):
                chance = random.randint(1,6)
                if chance <= 2:
                    poneMsg.append("pwny")

            if action == "$all" or (action == "!search" and channel == "#titties"):
                random.shuffle(boards)
                i = 0
                while i < len(boards)-1:
                    action = boards[i]
                    print(action)
                    result, piclist, Postno = allboards(action,poneCommand)
                    if "No images found" in result:
                        i+=1
                    else:
                        i = len(boards)
                print(result)
                poneMsg.append(result)

            if action == "$next":
                try:
                    if Postno == len(piclist)-1:
                        Postno = 0
                    else:
                        Postno += 1
                    print(piclist[Postno])
                    poneMsg.append(piclist[Postno])
                except:
                    poneMsg.append("There have been no recent searches.")

            for Msg in poneMsg:
                if testMode == True:
                    print(channel, Msg)
                else:
                    irc.send(channel, Msg)

    except Exception as e:
        with open("ponerr.log", "a") as f:
            f.write("{} - {}\n".format(timenow.strftime("%m/%d/%y %H:%M:%S"),e))
        print(traceback.format_exc())

sys.exit()
