# Python 3.10.4
# Flask 2.1.2
# Flaskの公式ドキュメント：https://flask.palletsprojects.com/en/2.0.x/
# python3の公式ドキュメント：https://docs.python.org/ja/3.9/
# python3の基礎文法のわかりやすいサイト：https://note.nkmk.me/python/
# 使用するモジュールのインポート
# pythonが提供しているモジュールのインポート
import json
import logging
import urllib.request
import urllib.parse
from xml.etree.ElementInclude import include
from flask import Flask, request, render_template
# 自分で作成したモジュールのインポート
from database import Database
import requests

from requests_oauthlib import OAuth1Session, OAuth1
from dateutil import parser
from pytz import timezone
import os
import re
import traceback
import time
import tweepy
import pymysql
import pymysql.cursors
import random
import numpy as np
from tensorflow import keras
import MeCab
from gensim.models import KeyedVectors
from flask import send_file

# Flaskクラスをnewしてappに代入
# gunicornの起動コマンドに使用しているのでここは変更しないこと
app = Flask(__name__)

# ログの設定
format = "%(asctime)s: %(levelname)s: %(pathname)s: line %(lineno)s: %(message)s"
logging.basicConfig(filename='/var/log/intern1/flask.log',
                    level=logging.DEBUG, format=format, datefmt='%Y-%m-%d %H:%M:%S')

tokens={}
with open("tokens.txt" , "r") as f:
    for l in f.readlines():
        tokens[l.split(",")[0]]=l.split(",")[1].replace("\n","")
##################################################################
# トークン関連
CK = tokens["twitter_CK"]
CS = tokens["twitter_CS"]
BT = tokens["twitter_BS"]
AT = tokens["twitter_AT"]
ATS = tokens["twitter_ATS"]
LTK= tokens["line_token"]
myurl=tokens["my_url"]
##################################################################

# 「/」にPOSTリクエストが来た場合、index関数が実行される


@app.route('/', methods=['post'])
def index():
    # 以下のコードでログを出力できる。出力先は「ログの設定」にあるファイル。コマンドラインに出力する場合はprintを使う。
    # logging.debug("こんにちは!")
    # POSTリクエストのbodyを取得
    
    body_binary = request.get_data()
    body = json.loads(body_binary.decode())
    logging.debug(body)
    if body["events"][0]["type"] == "message":
        replyToken = body["events"][0]["replyToken"]
        text = body["events"][0]["message"]["text"]
        if text == "つぶやきモード":
            sql_ins(body["events"][0]["source"]["userId"], 0)
        elif text == "うわさモード":
            sql_ins(body["events"][0]["source"]["userId"], 1)
        elif text == "大喜利モード":
            sql_ins(body["events"][0]["source"]["userId"], 2)
            with open("odai.txt", "r")as f:
                odai = f.readlines()[::-1]
            random.shuffle(odai)
            odai_rep(replyToken, odai[0].replace(
                "\n", ""), body["events"][0]["source"]["userId"])
        else:
            rep(replyToken, text, body["events"][0]["source"]["userId"])
    return "", 200


@app.route('/num', methods=['get'])
def ret_num():
    num = request.args.get("num")
    if int(num) > 9:
        num=9
    file_name = "number_pic/number_{}.png".format(num)
    return send_file(file_name, mimetype='image/png')


def rep(replyToken, text, id):
    url = 'https://api.line.me/v2/bot/message/reply/'
    tokens = "Bearer {}".format(LTK)
    result = []
    messages = []
    headers = {'Content-Type': "application/json", "Authorization": tokens}

    if sql_get(id) == None:
        sql_ins(id, 0)
    if "トレンド" in text or "話題" in text:
        result = trand_get()
        random.shuffle(result)
    else:
        if sql_get(id)["status"] == "0":
            result = tweetget(
                text+" min_replies:50 -min_replies:500 -has:media")
            logging.debug(result)
            if len(result) != 0:
                random.shuffle(result)
                try:
                    result = search_twitter_timeline("conversation_id:"+str(result[0]))
                except:
                    result=[]
        elif sql_get(id)["status"] == "1":
            result = search_twitter_timeline(text)
        else:
            result = hyouka_tweet(sql_get(id)["odai"]+"\n"+text)

    if len(result) >= 3:
        if sql_get(id)["status"] != "2":
            messages += [{"type": "text", "text": "🄰\n"+result[0]}]
            messages += [{"type": "text", "text": "🄱\n"+result[1]}]
            messages += [{"type": "text", "text": "🄲\n"+result[2]}]
        else:
            messages += [{"type": "image", "originalContentUrl": myurl+"/num?num={}".format(
                result[0]), "previewImageUrl":myurl+"/num?num={}".format(result[0])}]
            messages += [{"type": "image", "originalContentUrl": myurl+"/num?num={}".format(
                result[1]), "previewImageUrl":myurl+"/num?num={}".format(result[1])}]
            messages += [{"type": "image", "originalContentUrl": myurl+"/num?num={}".format(
                result[2]), "previewImageUrl":myurl+"/num?num={}".format(result[2])}]
    else:
        messages += [{"type": "sticker",
                      "packageId": "6136", "stickerId": "10551380"}]
        messages += [{"type": "text", "text": "ごめんね、今は喋れないんだ..."}]
    messages[-1]["quickReply"] = {
        "items": [
            {"type": "action",
             "action": {
                 "type": "message",
                 "label": "トレンド",
                 "text": "今のトレンドを教えて"
             }
             },
            {"type": "action",
             "action": {
                 "type": "message",
                 "label": "つぶやく",
                 "text": "つぶやきモード"
             }
             },
            {"type": "action",
             "action": {
                 "type": "message",
                 "label": "うわさ",
                 "text": "うわさモード"
             }
             },
            {"type": "action",
             "action": {
                 "type": "message",
                 "label": "大喜利",
                 "text": "大喜利モード"
             }
             },
        ]
    }
    values = {"replyToken": replyToken, 'messages': messages}
    r = requests.post(url, data=json.dumps(values), headers=headers)
    logging.debug(result)


def odai_rep(replyToken, text, id):
    url = 'https://api.line.me/v2/bot/message/reply/'
    tokens = "Bearer {}".format(LTK)
    result = []
    messages = []
    headers = {'Content-Type': "application/json", "Authorization": tokens}
    messages += [{"type": "text", "text": text}]
    values = {"replyToken": replyToken, 'messages': messages}
    r = requests.post(url, data=json.dumps(values), headers=headers)
    logging.debug(result)
    connection = pymysql.connect(host='localhost',
                                 user='intern1',
                                 password='hogehoge-123',
                                 database='intern1',
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)
    with connection:
        if sql_get(id) == None:
            with connection.cursor() as cursor:
                sql = "INSERT INTO `myTable` (`id`, `status`,`odai`) VALUES (%s, %s,%s)"
                cursor.execute(sql, (str(id), 2, text))
            connection.commit()
        else:
            with connection.cursor() as cursor:
                sql = "UPDATE `myTable` SET `status`=%s , `odai`=%s WHERE `id`=%s"
                cursor.execute(sql, (2, text, str(id)))
            connection.commit()

SEARCH_TWEETS_URL = 'https://api.twitter.com/2/tweets/search/recent'

def get_twitter_session():
    return OAuth1Session(CK, CS, AT, ATS)


def search_twitter_timeline(keyword, since='', until='', max_id=''):
    timelines = []
    points = []
    id = ''
    twitter = get_twitter_session()

    params = {'query': keyword, "tweet.fields": "attachments,author_id,context_annotations,conversation_id,created_at,entities,geo,id,in_reply_to_user_id,lang,possibly_sensitive,public_metrics,referenced_tweets,reply_settings,source,text,withheld"}
    params["expansions"] = "author_id"
    params["user.fields"] = "public_metrics,created_at,verified,description,location,id"
    params["max_results"] = 100
    if max_id != '':
        params['until_id'] = max_id
    if since != '':
        params['start_time'] = since
    if until != '':
        params['end_time'] = until

    print(params)
    req = twitter.get(SEARCH_TWEETS_URL, params=params)
    logging.debug(req.reason)

    if req.status_code == 200:
        search_timeline = json.loads(req.text)
        logging.debug(search_timeline)
        for tweet in search_timeline["data"]:
            id = str(tweet['id'])
            # 次の100件を取得したときにmax_idとイコールのものはすでに取得済みなので捨てる
            if max_id == str(tweet['id']):
                continue

            """timeline = {'id': tweet['id']
                , 'created_at': str(parser.parse(tweet['created_at']).astimezone(timezone('Asia/Tokyo')))
                , 'text': tweet['text']
                , "favorite_count":tweet['public_metrics']["like_count"]
                , "retweet_count":tweet['public_metrics']["retweet_count"]
                , "reply_count":tweet['public_metrics']["reply_count"]
                , 'user_id': tweet['author_id']
                , 'user_created_at': str(parser.parse(user['created_at']).astimezone(timezone('Asia/Tokyo')))
                , 'user_name': user['name']
                , 'user_screen_name': user['username']
                , 'user_description': user['description']
                , 'user_statuses_count': user["public_metrics"]['tweet_count']
                , 'user_followers_count': user["public_metrics"]['followers_count']
                , 'user_friends_count': user["public_metrics"]['following_count']
                , 'user_listed_count': user["public_metrics"]['listed_count']
            }"""
            timeline = {"text": tweet["text"]}
            logging.debug(timeline['text'])
            
            if "http" not in timeline["text"] and len(timeline["text"]) <= 25:
                timelines += [re.sub("@.* | #.*", "",
                                     timeline["text"]).replace("RT ", "")]
                point = tweet['public_metrics']["like_count"] + \
                    tweet['public_metrics']["retweet_count"] + \
                    tweet['public_metrics']["reply_count"]
                points += [point]
    else:
        logging.debug("ERROR: %d" % req.status_code)
    twitter.close()
    arg_sort = np.argsort(points)
    timelines = [timelines[i] for i in arg_sort[::-1]]

    return timelines


def tweetget(query):

    auth = tweepy.OAuthHandler(CK, CS)
    auth.set_access_token(AT, ATS)
    api = tweepy.API(auth)
    timeline = []

    flg = False
    for i in range(3):
        try:
            for status in tweepy.Cursor(api.search_tweets, q=query, count=100).items(100):
                logging.debug(status)
                timeline += [status.id]
            flg = True
        except:
            logging.debug(traceback.format_exc())
            timeline = []
        if flg or i == 2:
            break
        time.sleep(5)
    return timeline

def sql_ins(id, status):
    connection = pymysql.connect(host='localhost',
                                 user='intern1',
                                 password='hogehoge-123',
                                 database='intern1',
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)

    with connection:
        if sql_get(id) == None:
            with connection.cursor() as cursor:
                sql = "INSERT INTO `myTable` (`id`, `status`,`odai`) VALUES (%s, %s,null)"
                cursor.execute(sql, (str(id), str(status)))
            connection.commit()
        else:
            with connection.cursor() as cursor:
                sql = "UPDATE `myTable` SET `status`=%s WHERE `id`=%s"
                cursor.execute(sql, (str(status), str(id)))
            connection.commit()


def sql_get(id):
    connection = pymysql.connect(host='localhost',
                                 user='intern1',
                                 password='hogehoge-123',
                                 database='intern1',
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)

    with connection:

        with connection.cursor() as cursor:
            sql = "SELECT `status`,`odai` FROM `myTable` WHERE `id`=%s"
            cursor.execute(sql, (str(id),))
            result = cursor.fetchone()
            return result


def trand_get(woeid=23424856):
    auth = tweepy.OAuthHandler(CK, CS)
    auth.set_access_token(AT, ATS)
    api = tweepy.API(auth)
    timeline = []
    logging.debug(api.get_place_trends(id=woeid))
    timeline = []
    for t in api.get_place_trends(id=woeid)[0]["trends"][:3]:
        if len(search_twitter_timeline(t["name"])) != 0:
            text = search_twitter_timeline(t["name"])[0]
        else:
            text = ""
        timeline += ["trands:"+t["name"]+"\n" + text]
    return timeline


def hyouka_tweet(text):
    model = keras.models.load_model('judge.h5')
    wv = KeyedVectors.load_word2vec_format('./wiki.vec.pt', binary=True)
    mt = MeCab.Tagger('')
    vecs = word2vecs(text, mt, wv)
    pred = np.argmax(model.predict(np.array([vecs])))+1
    logging.debug(pred)
    hyouka = feature_word(text, mt, wv)
    logging.debug(hyouka)
    a_judge = str(int(pred+sum(hyouka)/5+hyouka[0]*5))  # かわいい重視
    b_judge = str(int(pred+sum(hyouka)/5+hyouka[1]*5))  # かっこいい重視
    c_judge = str(int(pred+sum(hyouka)/5+hyouka[2]*5))  # 怖い重視
    logging.debug(hyouka)
    result = [a_judge, b_judge, c_judge]
    return result


def word2vecs(word, mt, wv):
    vecs = []
    word_count = 0
    node = mt.parseToNode(word)
    while node:
        fields = node.feature.split(",")
        # 名詞、動詞、形容詞に限定
        if fields[0] == '名詞' or fields[0] == '動詞' or fields[0] == '形容詞':
            if node.surface in wv:
                vecs += [wv[node.surface]]
            else:
                vecs += [np.ones(200)]
            word_count += 1
        node = node.next
    if len(vecs) >= 20:
        vecs = vecs[:20]
    else:
        vecs = vecs+[np.zeros(200)]*(20-len(vecs))
    return vecs


def feature_word(word, mt, wv):
    feature_name = ["かわいい", "かっこいい", "怖い", "面白い", "すごい"]
    feature = []
    for f in feature_name:
        feature += [cos_sim(word2vec(f, mt, wv), word2vec(word, mt, wv))]
    return feature


def cos_sim(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))


def word2vec(word, mt, wv):
    sum_vec = np.zeros(200)
    word_count = 0
    node = mt.parseToNode(word)
    while node:
        fields = node.feature.split(",")
        if node.surface in wv:
            sum_vec += wv[node.surface]
            word_count += 1
        node = node.next

    return sum_vec / word_count
