# coding: utf-8
import tweepy
import traceback
import sqlite3
import time
import os

DEBUG = not True

#データベース接続
conn = sqlite3.connect('responceList.sqlite3')

#twitter認証
CK = os.getenv("CONSUMER_KEY", "")
CS = os.getenv("CONSUMER_SECRET", "")
AT = os.getenv("ACCESS_TOKEN", "")
AS = os.getenv("ACCESS_SECRET", "")

auth = tweepy.OAuthHandler(CK, CS)

auth.set_access_token(AT, AS)
api = tweepy.API(auth)

class Listener(tweepy.StreamListener):
    answer_num=0
    sql = "select count(*) from responce;"
    ret = conn.execute(sql)
    rows = ret.fetchall()
    subjectCount=rows[0][0]
    please_answer=[u"どう答えれば良いのかわかりません", u"どう返答するのが望ましいですか",u"どう返せばいいの？"]
    reply_answer=[u"覚えました", u"わかりました",u"ok"]
    me = api.me()

    teach = {}

    def on_status(self, status):
        author = status.author

        print('------------------------------')
        print(status.text)
        print(u"{name}({screen}) {created} via {src}\n".format(
            name=author.name,
            screen=author.screen_name,
            created=status.created_at,
            src=status.source))

        # dont reaction to me
        if author.id == self.me.id:
            return True

        if status.in_reply_to_user_id == self.me.id:
            t = self.teach.get(author.id)
            extact_text = self.extact_reply_word(status.text)


            if not t:
                # 登録済み単語の場合はリプライ
                rep = self.search_from_DB(extact_text, author.id)
                if rep:
                    self.reply(rep, status)
                    return True

                self.teach[author.id] = extact_text

                text = u"%sさん。%s\n現在の登録件数は%d" % (author.name, self.please_answer[self.answer_num], self.subjectCount)
                self.answer_num = (self.answer_num + 1) % 3
                self.reply(text, status)
            else:
                self.learn(self.teach[author.id], extact_text, status)
                text = u"%sさん。%s\n現在の登録件数は%d" % (author.name, self.reply_answer[self.answer_num], self.subjectCount)
                self.reply(text, status)

                self.teach[author.id] = None
        else:
            self.reaction(status)

        return True

    def on_event(self, event):
        print(event.event)
        if event.event == 'follow':
            api.create_friendship(event.source['id'])
            print(u"followed by %s %s" % (event.source['name'], event.source['screen_name']))

    def on_error(self, status_code):
        print('Got an error with status code: ' + str(status_code))
        return True

    def on_timeout(self):
        print('Timeout...')
        return True


    def extact_reply_word(self, text):
        tweet_part = text.split("@%s " % self.me.screen_name)
        return ''.join(tweet_part)

    def reply(self, reply, status):
        text = u"@%s %s" % (status.author.screen_name, reply)
        if not DEBUG:
            api.update_status(text, in_reply_to_status_id=status.id)

    def learn(self, src, dst, status):
        query = u"INSERT INTO RESPONCE VALUES(:src, :dst, :teacher, :ts);"
        if not DEBUG:
            conn.execute(query, [src, dst, status.author.id, status.created_at])
            self.subjectCount += 1

    def reaction(self, status):
        # try:
        if not DEBUG:
            text = self.search_from_DB(status.text)
            if text:
                api.update_status(text)
        # except tweepy.error.TweepError as te:
        #     text = u"エラーです。結構前に同じことを言っています。"+unicode(int(time.time()))
        #     api.update_status(status = text)
        # except :
        #     traceback.print_exc()

    def search_from_DB(self, word, user_id=None):
        if not user_id:
            query = u"SELECT bot_word FROM responce WHERE user_word=:word;"
            ret = conn.execute(query, [word])
        else:
            query = u"SELECT bot_word FROM responce WHERE user_word=:word AND teacher=:teacher;"
            ret = conn.execute(query, [word, user_id])
        rows = ret.fetchall()
        if rows == []:
            return None
        print rows[0]
        return rows[0][0]

# Twitterオブジェクトの生成
try:
    listener = Listener()
    stream = tweepy.Stream(auth, listener)
    if DEBUG:
        stream.sample()
    else:
        stream.userstream()
except KeyboardInterrupt:
    print u"きた"
    conn.commit()
    conn.close()
#参考サイト
#userstreamの使いかた
# http://ha1f-blog.blogspot.jp/2015/02/tweepypythonpip-tweepymac.html
