README
================================================================================
This readme file describes how to get, use and format the hand classified
classified tweets from the PSAIS project team for the naive Bayes
classification algorithm.

== ABOUT THE TRAINING DATASET
The data were collected and hand classified by the PSAIS project team.

== GET THE TRAINING DATASET
You can get the training dataset from the PSAIS project team.

== PREPARE THE DATA
Please check that all csv files have the same following structure:
timestamp; classification; user; tweet-message

Example:
Thu May 19 13:05:54 +0000 2016;neutral;CollectCardsNow;'Hello World Tweet!';


== CONVERT THE DATA
Put the UTF-8-encoded hand classified csv files in the the directory of this
readme file, where you also could find the converter.py file.
Now you can start running the converter.py file by using the terminal. If give
the program runs correctly, you could find three new csv files
(positive.csv, negative.csv and neutral.csv)in the results folder.

== ADD THE TRAINGS DATA TO NAIVE BAYES
Last you have to add the content of this three csv files to the positive.txt,
negative.txt and neutral.txt files inside the corpus folder.
