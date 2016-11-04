
import csv

PositiveTweetMessage = []
NegativeTweetMessage = []
NeutralTweetMessage = []

REPLACE_CHARS = ('Read more:', 'RT', 'b')
EXCLUDE_WORDS = ('https', 'http', '#', '@')

def main():
    values = csv.reader(open('training.1600000.processed.noemoticon.csv', 'r', encoding='utf-8'), delimiter=',')
    for row in values:
        try:
            if(row[0] == "4"):
                PositiveTweetMessage.append(row[5].strip())
            if(row[0] == "2"):
                NeutralTweetMessage.append(row[5].strip())
            if(row[0] == "0"):
                NegativeTweetMessage.append(row[5].strip())
        except:
            print("Error by getting the classification or message of the current tweet {}.".format(row))

    createNegCorpus(NegativeTweetMessage)
    createPosCorpus(PositiveTweetMessage)
    createNeutralCorpus(NeutralTweetMessage)


def decode_sentence(sentence):
    byte_string = bytes(sentence, 'utf-8')
    tweet_message = byte_string.decode('utf-8')

    return tweet_message


def createNegCorpus(NegativeTweetList):
    #  write negative tweets to text file
    negCorpus = open("results/negative.txt", "a")
    for tweet in NegativeTweetList:
        tweet = decode_sentence(tweet)
        tweet = filter_tweets(tweet)
        negCorpus.write(tweet + "\n")
    negCorpus.close()


def createPosCorpus(PositiveTweetList):
    #  write positive tweets to text file
    posCorpus = open("results/positive.txt", "a")
    for tweet in PositiveTweetList:
        tweet = decode_sentence(tweet)
        tweet = filter_tweets(tweet)
        posCorpus.write(tweet + "\n")
    posCorpus.close()


def createNeutralCorpus(NeutralTweetList):
    #  write neutral tweets to text file
    neutralCorpus = open("results/neutral.txt", "a")
    for tweet in NeutralTweetList:
        tweet = decode_sentence(tweet)
        tweet = filter_tweets(tweet)
        neutralCorpus.write(tweet + "\n")
    neutralCorpus.close()


def filter_tweets(sentence):
    for char in REPLACE_CHARS:
        sentence = sentence.replace(char, "")
    for char in EXCLUDE_WORDS:
        sentence = ' '.join(word for word in sentence.split(' ') if not word.startswith(char))

    return sentence


if __name__ == "__main__":
    main()
