README
================================================================================
This readme file describes how to get, use and format 1.6 Million machine
classified tweets from Sentiment140 as training data for the naive Bayes
classification algorithm.

== ABOUT THE TRAINING DATASET
The data comes from the Sentiment140 website. [http://help.sentiment140.com/]
The approach from the Sentiment140 team was unique because their training data
was automatically created, as opposed to having humans manual annotate tweets.
In their approach, they assume that any tweet with positive emoticons, like :),
were positive, and tweets with negative emoticons, like :(, were negative.
They used the Twitter Search API to collect these tweets by using keyword
search. This is also described in their paper:
[http://cs.stanford.edu/people/alecmgo/papers/TwitterDistantSupervision09.pdf]

== GET THE TRAINING DATASET
A zip-file with the 1.6 Million tweets could be downloaded on the official
Website of Sentiment140. [http://help.sentiment140.com/for-students/]
You also could use this direct Link for downloading the 81.4 MB zip-file:
--> http://cs.stanford.edu/people/alecmgo/trainingandtestdata.zip

== PREPARE THE DATA
Before you could converter the data by using the converter.py program, you have
to save them in UTF-8. (You can do that with Sublime Text for example)

== CONVERT THE DATA
Put the UTF-8-encoded training.1600000.processed.noemoticon.csv file in the the
directory of this readme file, where you also could find the converter.py file.
Now you can start running the converter.py file by using the terminal. If give
the program gives no error message, you could find three new csv files
(positive.csv, negative.csv and neutral.csv)in the results folder.

== ADD THE TRAINGS DATA TO NAIVE BAYES
Last you have to add the content of this three csv files to the positive.txt,
negative.txt and neutral.txt files inside the corpus folder.
