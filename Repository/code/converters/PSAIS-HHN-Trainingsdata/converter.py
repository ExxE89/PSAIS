
import csv
import os

PositiveTweetMessage = []
NegativeTweetMessage = []
NeutralTweetMessage = []

REPLACE_CHARS = ('Read more:', 'RT', 'b')
EXCLUDE_WORDS = ('https', 'http', '#', '@')


def main():
    for file in os.listdir(os.curdir):
	    if file.endswith(".csv"):
	        values = csv.reader(open(file,'r', encoding='latin-1'), delimiter=';')
	        for row in values:
	            tweet = row[3].strip()
	            try:
	                if(row[1] == "positiv"):
	                    PositiveTweetMessage.append(tweet)
	                if(row[1] == "neutral"):
	                    NeutralTweetMessage.append(tweet)
	                if(row[1] == "negativ"):
	                    NegativeTweetMessage.append(tweet)
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
