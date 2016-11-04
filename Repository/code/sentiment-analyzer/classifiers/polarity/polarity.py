import textblob


def classify(text):
    analysis_result = textblob.TextBlob(text)
    
    return {
        "polarity": analysis_result.sentiment.polarity,
        "subjectivity": analysis_result.sentiment.subjectivity,
    }
