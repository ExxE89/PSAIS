def polarity = doc['sentiment_' + classifier].value

if (polarity > 0.1) {
    return "pos"
}

if (polarity < -0.1) {
    return "neg"
}

return "neutral"
