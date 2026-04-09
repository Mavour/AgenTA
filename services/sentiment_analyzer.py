import logging
from typing import List, Dict
from collections import Counter

logger = logging.getLogger(__name__)

BULLISH_WORDS = [
    "bullish", "surge", "rally", "gain", "rise", "up", "positive", "growth",
    "breakout", "moon", " ATH ", "high", "buy", "long", "call", "accumulate",
    "support", "break", "soar", "jump", "boost", "recovery", "rebound", "bull run"
]

BEARISH_WORDS = [
    "bearish", "crash", "drop", "fall", "down", "negative", "decline", "sell",
    "dump", "breakdown", "bear", "short", "put", "lower", "break support",
    "plunge", "sink", "slump", "correction", "rejection", "failed", "danger"
]

NEUTRAL_WORDS = [
    "sideways", "consolidate", "range", "wait", "monitor", "neutral", "flat"
]


def analyze_text_sentiment(text: str) -> str:
    text_lower = text.lower()
    
    bullish_count = sum(1 for word in BULLISH_WORDS if word in text_lower)
    bearish_count = sum(1 for word in BEARISH_WORDS if word in text_lower)
    
    if bullish_count > bearish_count + 1:
        return "bullish"
    elif bearish_count > bullish_count + 1:
        return "bearish"
    return "neutral"


def analyze_news_sentiment(news_list: List[Dict]) -> Dict:
    if not news_list:
        return {"sentiment": "neutral", "bullish": 0, "bearish": 0, "neutral": 0, "total": 0}
    
    sentiments = []
    for news in news_list:
        title = news.get("title", "")
        sentiment = analyze_text_sentiment(title)
        sentiments.append(sentiment)
    
    counts = Counter(sentiments)
    total = len(sentiments)
    
    return {
        "sentiment": max(counts, key=counts.get),
        "bullish": counts.get("bullish", 0),
        "bearish": counts.get("bearish", 0),
        "neutral": counts.get("neutral", 0),
        "total": total,
        "bullish_pct": round((counts.get("bullish", 0) / total) * 100, 1),
        "bearish_pct": round((counts.get("bearish", 0) / total) * 100, 1),
        "neutral_pct": round((counts.get("neutral", 0) / total) * 100, 1)
    }


def analyze_twitter_sentiment(tweets: List[Dict]) -> Dict:
    if not tweets:
        return {"sentiment": "neutral", "bullish": 0, "bearish": 0, "neutral": 0, "total": 0}
    
    sentiments = []
    for tweet in tweets:
        text = tweet.get("text", "")
        sentiment = analyze_text_sentiment(text)
        sentiments.append(sentiment)
    
    counts = Counter(sentiments)
    total = len(sentiments)
    
    return {
        "sentiment": max(counts, key=counts.get),
        "bullish": counts.get("bullish", 0),
        "bearish": counts.get("bearish", 0),
        "neutral": counts.get("neutral", 0),
        "total": total,
        "bullish_pct": round((counts.get("bullish", 0) / total) * 100, 1),
        "bearish_pct": round((counts.get("bearish", 0) / total) * 100, 1),
        "neutral_pct": round((counts.get("neutral", 0) / total) * 100, 1)
    }


def combine_sentiments(news_sentiment: Dict, twitter_sentiment: Dict = None, price_sentiment: Dict = None) -> Dict:
    chart_weight = 0.5
    price_weight = 0.3
    twitter_weight = 0.2
    
    news_score = (
        (news_sentiment.get("bullish_pct", 0) / 100) * 1 +
        (news_sentiment.get("neutral_pct", 0) / 100) * 0 +
        (news_sentiment.get("bearish_pct", 0) / 100) * -1
    )
    
    price_score = 0
    if price_sentiment and price_sentiment.get("total", 0) > 0:
        price_score = (
            (price_sentiment.get("gainers_pct", 0) / 100) * 1 +
            (price_sentiment.get("losers_pct", 0) / 100) * -1
        )
    
    if twitter_sentiment and twitter_sentiment.get("total", 0) > 0:
        twitter_score = (
            (twitter_sentiment.get("bullish_pct", 0) / 100) * 1 +
            (twitter_sentiment.get("neutral_pct", 0) / 100) * 0 +
            (twitter_sentiment.get("bearish_pct", 0) / 100) * -1
        )
        combined_score = (news_score * 0.5) + (price_score * 0.3) + (twitter_score * 0.2)
    else:
        combined_score = (news_score * 0.6) + (price_score * 0.4)
    
    if combined_score > 0.2:
        overall_sentiment = "bullish"
    elif combined_score < -0.2:
        overall_sentiment = "bearish"
    else:
        overall_sentiment = "neutral"
    
    confidence = min(abs(combined_score) * 50 + 50, 95)
    
    return {
        "sentiment": overall_sentiment,
        "confidence": round(confidence, 1),
        "news": news_sentiment,
        "price": price_sentiment,
        "twitter": twitter_sentiment,
        "score": round(combined_score, 2)
    }


def format_sentiment_summary(sentiment_data: Dict) -> str:
    lines = []
    
    news = sentiment_data.get("news", {})
    if news and news.get("total", 0) > 0:
        lines.append("📰 *Sentimen News:*")
        lines.append(f"  🟢 Bullish: {news.get('bullish_pct', 0)}%")
        lines.append(f"  🔴 Bearish: {news.get('bearish_pct', 0)}%")
        lines.append(f"  ⚪ Neutral: {news.get('neutral_pct', 0)}%")
    
    price = sentiment_data.get("price", {})
    if price and price.get("total", 0) > 0:
        lines.append("")
        lines.append("📊 *Sentimen Harga (Top 20):*")
        lines.append(f"  🟢 Gainers: {price.get('gainers', 0)} coin ({price.get('gainers_pct', 0)}%)")
        lines.append(f"  🔴 Losers: {price.get('losers', 0)} coin ({price.get('losers_pct', 0)}%)")
    
    twitter = sentiment_data.get("twitter", {})
    if twitter and twitter.get("total", 0) > 0:
        lines.append("")
        lines.append("🐦 *Sentimen Twitter:*")
        lines.append(f"  🟢 Bullish: {twitter.get('bullish_pct', 0)}%")
        lines.append(f"  🔴 Bearish: {twitter.get('bearish_pct', 0)}%")
    
    if not lines:
        lines.append("⚠️ Data tidak tersedia")
    
    return "\n".join(lines)


if __name__ == "__main__":
    test_news = [
        {"title": "Bitcoin surges to new ATH as institutional interest grows"},
        {"title": "Ethereum rally continues amid positive sentiment"},
        {"title": "Crypto market shows signs of correction"}
    ]
    result = analyze_news_sentiment(test_news)
    print(result)