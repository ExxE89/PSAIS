# Source: http://stackoverflow.com/q/20827741

import argparse
import collections
import itertools
import logging
import lzma
import os
import pickle
import random
import re

import nltk

try:
    import pyspark
except ImportError:
    pyspark = None

BASEDIR = os.path.dirname(__file__)
CORPUS_BASEDIR = os.path.join(BASEDIR, "corpus")
INFORMATIVE_FEATURES = 15
#PICKLE_FILENAME = os.path.join(BASEDIR, "naive_bayes.pickle.xz")
STOP_WORDS_FILENAME = "stop_words.txt"
TEST_SIZE = 1000
WHITESPACE_PATTERN = re.compile(r"\s{2,}")
WORD_PATTERN = re.compile(r"[^a-z ]")
WORD_SAMPLE_SIZE = 10000

TEST_SENTENCES = (
    "I'm feeling so good today!",
    "I'm feeling so bad today!",
    "I'm feeling so happy today!",
    "I'm feeling so nice today!",
    "I hate you so much.",
    "I love this sandwich.",
    "This is an amazing place!",
    "I feel very good about these beers.",
    "This is my best work.",
    "What an awesome view",
    "I do not like this restaurant",
    "I am tired of this stuff.",
    "I can't deal with this",
    "He is my sworn enemy!",
    "My boss is horrible.",
    "The beer was good.",
    "I do not enjoy my job",
    "I ain't feeling dandy today.",
    "I feel amazing!",
    "Gary is a friend of mine.",
    "I can't believe I'm doing this.",
)

cached_classifier = None


def check_for_empty_sentences(training_set):
    empty_sentences = tuple(filter(lambda x: True not in x[0].values(), training_set))
    
    if empty_sentences:
        logger.error("Got {} empty sentences".format(len(empty_sentences)))


def classify(text):
    words = get_word_list(text)
    
    word_map = {}
    
    for word in words:
        word_map[word] = True
    
    classifier = get_classifier()
    probability_distribution = classifier.prob_classify(word_map)
    
    sample = probability_distribution.max()
    probability = probability_distribution.prob(sample)
    
    polarity = map_number_range(probability, 0.5, 1, 0, 1)
    
    if sample == "neg":
        polarity *= -1
    
    return {
        "polarity": polarity,
        "probability": probability,
        "subjectivity": None,
    }


def get_all_words():
    stop_words = get_stop_words()
    all_words = collections.Counter()
    
    sentences = itertools.chain(
        get_positive_sentences(),
        get_negative_sentences(),
        get_neutral_sentences(),
    )
    
    for sentence in sentences:
        words = get_word_list(sentence)
        words = filter(lambda word: word not in stop_words, words)
        all_words.update(words)
    
    logger.info("Parsed {} different words".format(len(all_words)))
    logger.info("Taking {} most common words".format(WORD_SAMPLE_SIZE))
    all_words = all_words.most_common(WORD_SAMPLE_SIZE)
    all_words = [word[0] for word in all_words]
    
    return all_words


def get_classifier():
    global cached_classifier
    
    if cached_classifier:
        return cached_classifier

    filename = os.path.join(BASEDIR, "naive_bayes.pickle.xz")

    if pyspark:
        filename = pyspark.SparkFiles.get(os.path.basename(filename))

    if os.path.exists(filename):
        logger.debug("Using cached classifier ...")
        cached_classifier = get_saved_classifier()
        return cached_classifier
        
    logger.info("Training new classifier with corpus ...")
    classifier = get_new_classifier()
    
    logger.info("Caching classifier ...")
    save_classifier(classifier)
    
    return classifier


def get_new_classifier(print_accuracy=False):
    logger.info("Loading all words ...")
    all_words = get_all_words()
    logger.info("Using {} words".format(len(all_words)))
    
    training_set = get_labeled_training_set(all_words)
    
    if print_accuracy:
        logger.info("Loading training set into memory ...")
        training_set = list(training_set)
        
        logger.info("Checking for parse errors ...")
        check_for_empty_sentences(training_set)
        
        logger.info("Shuffling for testing set ...")
        random.shuffle(training_set)
        
        testing_set = training_set[:TEST_SIZE]
        training_set = training_set[TEST_SIZE:]
        
        logger.info("Training set size: {}".format(len(training_set)))
        logger.info("Testing set size: {}".format(len(testing_set)))
    
    logger.info("Training classifier ...")
    classifier = nltk.NaiveBayesClassifier.train(training_set)
    classifier.show_most_informative_features(INFORMATIVE_FEATURES)
    
    for sentence in TEST_SENTENCES:
        word_map = get_word_map(all_words, sentence)
        logger.info(sentence)
        
        prob = classifier.prob_classify(word_map)
        
        for sample in prob.samples():
            logger.info("{} {:.1f} %".format(sample, prob.prob(sample) * 100))
    
    if print_accuracy:
        logger.info("Measuring accuracy ...")
        accuracy = nltk.classify.accuracy(classifier, testing_set) * 100
        logger.info("Accuracy: {:.1f}".format(accuracy))
    
    return classifier


def get_positive_sentences():
    filename = os.path.join(CORPUS_BASEDIR, "positive.txt")

    if pyspark:
        filename = pyspark.SparkFiles.get(os.path.basename(filename))
    
    return get_sentences(filename)

def get_negative_sentences():
    filename = os.path.join(CORPUS_BASEDIR, "negative.txt")

    if pyspark:
        filename = pyspark.SparkFiles.get(os.path.basename(filename))
    
    return get_sentences(filename)


def get_neutral_sentences():
    filename = os.path.join(CORPUS_BASEDIR, "neutral.txt")

    if pyspark:
        filename = pyspark.SparkFiles.get(os.path.basename(filename))
    
    return get_sentences(filename)


def get_labeled_training_set(all_words):
    training_sets = (
        ("pos", get_positive_sentences()),
        ("neg", get_negative_sentences()),
        ("neutral", get_neutral_sentences()),
    )
    
    for sentiment, sentences in training_sets:
        for word_map in get_word_maps(all_words, sentences):
            # Do not add sentences that only consist of stop words or exotic words.
            # They add no value to the training set.
            if True not in word_map.values():
                continue
            
            yield word_map, sentiment


def get_logger():
    logger = logging.getLogger("psais.classifier.naivebayes")
    logger.setLevel(logging.DEBUG)
    
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    
    logger.addHandler(ch)
    
    return logger


def get_saved_classifier():
    filename = os.path.join(BASEDIR, "naive_bayes.pickle.xz")

    if pyspark:
        filename = pyspark.SparkFiles.get(os.path.basename(filename))

    with lzma.open(filename) as fh:
        classifier = pickle.load(fh)
    
    return classifier


def get_sentences(filename):
    with open(filename, errors="ignore") as fh:
        for line in fh:
            yield line


def get_stop_words():
    stop_words = []
    
    filename = os.path.join(BASEDIR, STOP_WORDS_FILENAME)

    if pyspark:
        filename = pyspark.SparkFiles.get(os.path.basename(filename))

    with open(filename) as fh:
        for line in fh:
            line = line.strip()
            line = line.lower()
            line = WORD_PATTERN.sub("", line)
            
            if not line:
                continue
            
            stop_words.append(line)
    
    return stop_words


def get_word_list(sentence):
    sentence = sentence.lower()
    sentence = WORD_PATTERN.sub("", sentence)
    sentence = WHITESPACE_PATTERN.sub(" ", sentence)
    sentence = sentence.strip()
    
    words = sentence.split(" ")
    return words


def get_word_map(all_words, sentence):
    word_map = {}
    words = get_word_list(sentence)
    
    for word in all_words:
        #word_map[word] = word in words
        # Much more memory efficient:
        if word in words:
            word_map[word] = True
    
    return word_map


def get_word_maps(all_words, sentences):
    for sentence in sentences:
        yield get_word_map(all_words, sentence)


def map_number_range(number, input_start, input_end, output_start, output_end):
    # Source: http://stackoverflow.com/a/5732117
    input_range = input_end - input_start
    output_range = output_end - output_start
    
    return (number - input_start) * output_range / input_range + output_start


def save_classifier(classifier):
    filename = os.path.join(BASEDIR, "naive_bayes.pickle.xz")

    if pyspark:
        filename = pyspark.SparkFiles.get(os.path.basename(filename))
    
    with lzma.open(filename, "wb", preset=9 | lzma.PRESET_EXTREME) as fh:
        pickle.dump(classifier, fh)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--accuracy", action="store_true", help="only print accuracy, don't create cached classifier")
    parser.add_argument("-t", "--test", help="classify a test string")
    
    args = parser.parse_args()
    
    if args.test:
        print(classify(args.test))
        return
    
    classifier = get_new_classifier(args.accuracy)
    
    if not args.accuracy:
        logger.info("Caching classifier ...")
        save_classifier(classifier)
    

logger = get_logger()

if __name__ == "__main__":
    main()
