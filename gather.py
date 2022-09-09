import tweepy
import numpy as np
import time
import traceback
import pymysql
import pymysql.cursors

tokens={}
with open("tokens.txt" , "r")as f:
    for l in f.readlines():
        tokens[l.split(",")[0]]=l.split(",")[1].replace("\n","")
##################################################################
# トークン関連
CK = tokens["twitter_CK"]
CS = tokens["twitter_CS"]
BT = tokens["twitter_BT"]
AT = tokens["twitter_AT"]
ATS = tokens["twitter_ATS"]
LTK= tokens["line_token"]
##################################################################

def point2judge(point):
    if point>10000:
        return 10
    elif point>7500:
        return 9
    elif point>5000:
        return 8
    elif point>2500:
        return 7
    elif point>1000:
        return 6
    elif point>500:
        return 5
    elif point>100:
        return 4
    elif point>50:
        return 3
    elif point>10:
        return 2
    else:
        return 1

def tweetget_v2(query):
    api = tweepy.Client(bearer_token=BT, consumer_key=CK, consumer_secret=CS,
                        access_token=AT, access_token_secret=ATS, wait_on_rate_limit=True)
    timeline = []
    flg = False
    for i in range(3):
        try:
            #print(api.search_recent_tweets(query, max_results=100,).data)
            tweetfield="public_metrics"
            for d in api.search_recent_tweets(query, max_results=100,tweet_fields=tweetfield).data:
                timeline += [d]
            flg = True
        except:
            print(traceback.format_exc())
            timeline = []
        if flg or i == 2:
            break
        time.sleep(5)
    return timeline

def trand_get(woeid=23424856):
    auth = tweepy.OAuthHandler(CK, CS)
    auth.set_access_token(AT, ATS)
    api = tweepy.API(auth)
    timeline = []
    for t in api.get_place_trends(id=woeid)[0]["trends"]:
        timeline+=tweetget_v2(t["name"]+" -is:retweet -is:reply")
    for t in timeline:
        point=t['public_metrics']["like_count"]+t['public_metrics']["reply_count"]+t['public_metrics']["retweet_count"]
        sql_ins(t.id,t.text,point,point2judge(point))
        #print(t)
    
def sql_ins(id, text, point, judge):
    # Connect to the database
    connection = pymysql.connect(host='localhost',
                                 user='intern1',
                                 password='hogehoge-123',
                                 database='intern1',
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)

    with connection:
        if sql_get(id) == None:
            with connection.cursor() as cursor:
                # Create a new record
                sql = "INSERT INTO `text_database` (`tweetid`, `text`, `point`, `judge`) VALUES (%s, %s, %s, %s)"
                cursor.execute(sql, (str(id), str(text), int(point), int(judge)))
            # connection is not autocommit by default. So you must commit to save
            # your changes.
            connection.commit()
        else:
            with connection.cursor() as cursor:
                # Create a new record
                sql = "UPDATE `text_database` SET `text`=%s, `point`=%s, `judge`=%s WHERE `tweetid`=%s"
                cursor.execute(sql, (str(text), int(point), int(judge),str(id)))
            # connection is not autocommit by default. So you must commit to save
            # your changes.
            connection.commit()

def sql_get(id):
    # Connect to the database
    connection = pymysql.connect(host='localhost',
                                 user='intern1',
                                 password='hogehoge-123',
                                 database='intern1',
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)

    with connection:

        with connection.cursor() as cursor:
            # Read a single record
            sql = "SELECT `text`, `point`, `judge` FROM `text_database` WHERE `tweetid`=%s"
            cursor.execute(sql, (str(id),))
            result = cursor.fetchone()
            return result

if __name__=="__main__":
    trand_get()