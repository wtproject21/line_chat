#from turtle import shape
from webbrowser import get
import tweepy
import numpy as np
import time
import traceback
from gensim.models import KeyedVectors
import pymysql
import pymysql.cursors
import random
import MeCab
from keras.models import Sequential
from keras.layers import LSTM, Dense, Embedding, Dropout
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.metrics import classification_report
import os

os.environ["CUDA_VISIBLE_DEVICES"]="-1" 
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

wv = KeyedVectors.load_word2vec_format('./wiki.vec.pt', binary=True)
mt = MeCab.Tagger('')

def word2vecs(word):
    vecs=[]
    word_count = 0
    node = mt.parseToNode(word)
    while node:
        fields = node.feature.split(",")
        # 名詞、動詞、形容詞に限定
        if fields[0] == '名詞' or fields[0] == '動詞' or fields[0] == '形容詞':
            if node.surface in wv:
                vecs += [wv[node.surface]]
            else:
                vecs+=[np.ones(200)]
            word_count += 1
        node = node.next
    if len(vecs)>=20:
        vecs=vecs[:20]
    else:
        vecs=vecs+[np.zeros(200)]*(20-len(vecs))
    return vecs


def main():
    ids=get_ids()
    model = Sequential()
    model.add(LSTM(128, return_sequences=False))
    model.add(Dropout(0.5))
    model.add(Dense(10, activation='softmax'))
    model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

    callbacks = [EarlyStopping(monitor='val_loss',
                           patience=5, # ここで指定したエポック数の間改善がないと停止
                           verbose=1,
                           mode='max'),
                ]
    test=ids[int(len(ids)*0.9):]
    train=ids[:int(len(ids)*0.9)]
    epochs=32
    batchs=5
    for i in range(epochs):
        random.shuffle(train)
        print("{}epochs".format(i))
        for j in range(batchs):
            X_train,y_train,X_valid,y_valid=make_data_ids(ids[int(j*len(train)/batchs):int((j+1)*len(train)/batchs)])
            history = model.fit(X_train, y_train, epochs=1, batch_size=10, validation_data=(X_valid, y_valid), callbacks=callbacks)
    X_test,y_test=make_test(test)
    y_pred =  model.predict(X_test)
    model.save("judge.h5")
    print(classification_report(np.argmax(y_test, axis=1), np.argmax(y_pred, axis=1)))
    
def make_data():
    # Connect to the database
    connection = pymysql.connect(host='localhost',
                                 user='intern1',
                                 password='hogehoge-123',
                                 database='intern1',
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)

    with connection:
        with connection.cursor() as cursor:
            sql = "SELECT `text`, `point`, `judge` FROM `text_database` "
            cursor.execute(sql)
            result = cursor.fetchall()

    data=[[result[i]["text"],result[i]["judge"]] for i in range(len(result))]

    #print(data)
    random.shuffle(data)
    train=data[:int(len(data)*0.8)]
    valid=data[int(len(data)*0.8):int(len(data)*0.9)]
    test=data[int(len(data)*0.9):]
    X_train=[word2vecs(r[0]) for r in train]
    y_train=[np.array([1 if r[1]==i else 0 for i in range(10)]) for r in train]
    X_valid=[word2vecs(r[0]) for r in valid]
    y_valid=[np.array([1 if r[1]==i else 0 for i in range(10)]) for r in valid]
    X_test=[word2vecs(r[0]) for r in test]
    y_test=[np.array([1 if r[1]==i else 0 for i in range(10)]) for r in test]

    return X_train,y_train,X_valid,y_valid,X_test,y_test

def make_data_ids(ids):
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
            result=[]
            sql = "SELECT `text`, `point`, `judge` FROM `text_database` WHERE `tweetid`in ({})".format(",".join(["%s"]*len(ids)))
            cursor.execute(sql,tuple(ids))
            result =cursor.fetchall()

    #print(result)
    data=[[result[i]["text"],result[i]["judge"]] for i in range(len(result))]

    #print(data)
    random.shuffle(data)
    train=data[:int(len(data)*0.8)]
    valid=data[int(len(data)*0.8):]
    X_train=np.array([word2vecs(r[0]) for r in train])
    y_train=np.array([np.array([1 if r[1]==i else 0 for i in range(10)]) for r in train])
    X_valid=np.array([word2vecs(r[0]) for r in valid])
    y_valid=np.array([np.array([1 if r[1]==i else 0 for i in range(10)]) for r in valid])
    return X_train,y_train,X_valid,y_valid

def make_test(ids):
    connection = pymysql.connect(host='localhost',
                                 user='intern1',
                                 password='hogehoge-123',
                                 database='intern1',
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)

    with connection:
        with connection.cursor() as cursor:
            # Read a single record
            result=[]
            sql = "SELECT `text`, `point`, `judge` FROM `text_database` WHERE `tweetid`in ({})".format(",".join(["%s"]*len(ids)))
            cursor.execute(sql,tuple(ids))
            result =cursor.fetchall()
    data=[[result[i]["text"],result[i]["judge"]] for i in range(len(result))]
    X_train=np.array([word2vecs(r[0]) for r in data])
    y_train=np.array([np.array([1 if r[1]==i else 0 for i in range(10)]) for r in data])
    return X_train,y_train

def get_ids():
    connection = pymysql.connect(host='localhost',
                                 user='intern1',
                                 password='hogehoge-123',
                                 database='intern1',
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)

    with connection:
        with connection.cursor() as cursor:
            # Read a single record
            sql = "SELECT `tweetid` FROM `text_database` WHERE `judge`!=1"
            cursor.execute(sql)
            result = list(cursor.fetchall())
            sql = "SELECT `tweetid` FROM `text_database` WHERE `judge`=1"
            cursor.execute(sql)
            result+=random.sample(cursor.fetchall(),10000)
    random.shuffle(result)
    return [r["tweetid"] for r in result]

if __name__=="__main__":
    main()