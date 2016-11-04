
import json
import csv

from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream
import langdetect


ckey=""
csecret=""
atoken=""
asecret=""

# keywords or tags to filter
terms = ['apple']

writer = csv.writer(open('', 'w', newline=''))

class TweetStreamListener(StreamListener):

    def on_data(self, data):

        # decode json
        dict_data = json.loads(data)

        if 'text' in dict_data:
            try:
                if langdetect.detect(dict_data["text"]) == "en":
                    data = [dict_data["created_at"], dict_data["user"]["screen_name"], dict_data["text"].encode('utf-8')] 
                    print (data)
                    writer.writerow(data)
            except langdetect.lang_detect_exception.LangDetectException:
                pass
        else:
            pass

        return True


    def on_error(self, status):
        print (status)

if __name__ == '__main__':

    # create instance of the tweepy tweet stream listener
    listener = TweetStreamListener()

    # set twitter keys/tokens
    auth = OAuthHandler(ckey, csecret)
    auth.set_access_token(atoken, asecret)

    # create instance of the tweepy stream
    stream = Stream(auth, listener)

    # search twitter for keyword
    stream.filter(track=terms)
