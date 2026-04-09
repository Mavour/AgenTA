import logging
from typing import Dict, Optional, List
from services.news_fetcher import fetch_all_news, get_market_overview, get_market_sentiment_from_prices
from services.sentiment_analyzer import (
    analyze_news_sentiment, 
    analyze_price_sentiment,
    analyze_twitter_sentiment, 
    combine_sentiments,
    format_sentiment_summary
)
from services.twitter_scraper import fetch_crypto_tweets, fetch_influencer_tweets, check_cookie_status

logger = logging.getLogger(__name__)


def extract_chart_signal(analysis_text: str) -> Dict:
    text_lower = analysis_text.lower()
    
    bullish_keywords = ["bullish", "naik", "uptrend", "buy", "long", "buy call", "call", "momentum", "positif"]
    bearish_keywords = ["bearish", "turun", "downtrend", "sell", "short", "put", "sell call", "negatif"]
    neutral_keywords = ["sideways", "konsolidasi", "netral"]
    
    bullish_count = sum(1 for word in bullish_keywords if word in text_lower)
    bearish_count = sum(1 for word in bearish_keywords if word in text_lower)
    neutral_count = sum(1 for word in neutral_keywords if word in text_lower)
    
    trend = "neutral"
    score = 0
    
    if bullish_count > bearish_count + 1:
        trend = "bullish"
        score = min(bullish_count * 15, 80)
    elif bearish_count > bullish_count + 1:
        trend = "bearish"
        score = -min(bearish_count * 15, 80)
    elif neutral_count > 0:
        trend = "sideways"
        score = 0
    
    strength_match = analysis_text.lower().split("kekuatan")[1].split("/")[0].strip() if "kekuatan" in analysis_text.lower() else "5"
    try:
        strength = int(strength_match.split()[0])
    except:
        strength = 5
    
    return {
        "trend": trend,
        "strength": strength,
        "score": score,
        "source": "chart"
    }


def get_market_prediction(chart_analysis: str = None, pair: str = "BTC") -> Dict:
    result = {
        "chart": None,
        "news": None,
        "price": None,
        "twitter": None,
        "combined": None,
        "timestamp": None
    }
    
    if chart_analysis:
        chart_signal = extract_chart_signal(chart_analysis)
        result["chart"] = chart_signal
    
    try:
        all_news = fetch_all_news(limit=15)
        
        news_list = []
        for source, items in all_news.items():
            news_list.extend(items)
        
        if news_list and any("change_24h" in item for item in news_list):
            news_sentiment = analyze_price_sentiment(news_list)
        else:
            news_sentiment = analyze_news_sentiment(news_list)
        result["news"] = news_sentiment
        
        price_sentiment = get_market_sentiment_from_prices()
        result["price"] = price_sentiment
        
        twitter_sentiment = None
        cookie_status = check_cookie_status()
        
        if cookie_status.get("status") == "active":
            influencer_tweets = fetch_influencer_tweets(limit=30)
            if influencer_tweets:
                twitter_sentiment = analyze_twitter_sentiment(influencer_tweets)
                result["twitter"] = twitter_sentiment
            else:
                tweets = fetch_crypto_tweets([pair, "Bitcoin", "Ethereum"], limit=20)
                if tweets:
                    twitter_sentiment = analyze_twitter_sentiment(tweets)
                    result["twitter"] = twitter_sentiment
        
        result["combined"] = combine_sentiments(news_sentiment, twitter_sentiment, price_sentiment)
        
    except Exception as e:
        logger.error(f"Error getting market prediction: {e}")
    
    return result


def format_market_prediction(prediction: Dict, pair: str = "BTC") -> str:
    combined = prediction.get("combined", {})
    chart = prediction.get("chart")
    price = prediction.get("price", {})
    news = prediction.get("news")
    twitter = prediction.get("twitter")
    
    coin = pair.upper() if pair else "BTC"
    
    lines = []
    
    has_data = False
    
    if chart:
        trend = chart.get("trend", "netral").lower()
        trend_emoji = "🟢" if trend == "bullish" else "🔴" if trend == "bearish" else "⚪"
        strength = chart.get("strength", 5)
        lines.append(f"📊 *{coin}:* {trend_emoji} {trend.upper()} ({strength}/10)")
        has_data = True
    
    try:
        from services.news_fetcher import fetch_coingecko_news, get_news_with_context
        
        prices = fetch_coingecko_news(20)
        coin_change = {}
        for p in prices:
            change24h = p.get("change_24h", 0)
            price = p.get("price", 0)
            title = p.get("title", "")
            if "BTC" in title.upper() or price and 65000 < price < 72000:
                coin_change["BTC"] = change24h
            elif "ETH" in title.upper() or price and 2000 < price < 2500:
                coin_change["ETH"] = change24h
        
        coin_price = coin_change.get(coin, 0)
        
        if coin_price:
            has_data = True
        
        ctx = get_news_with_context(coin=coin)
        news_items = ctx.get("rss", [])[:5]
        
        if not news_items:
            news_items = ctx.get("mock", [])[:3]
        
        if not coin_price and not news_items:
            lines.append(f"\n⚠️ {coin}: Data tidak tersedia")
        
        if coin_price:
            pct = f"{coin_price:+.2f}%"
            if coin_price < -1:
                lines.append(f"\n📉 {coin}: {pct} - tekanan jual")
            elif coin_price > 1:
                lines.append(f"\n📈 {coin}: {pct} - momentum positif")
            else:
                lines.append(f"\n💰 {coin}: {pct} - netral")
        
        if news_items:
            found_coin = ctx.get("coin", "").upper()
            if found_coin and found_coin in coin.upper():
                lines.append(f"\n📰 *{found_coin} News:*")
            else:
                lines.append(f"\n📰 *News:*")
            for item in news_items:
                title = item.get("title", "")[:50]
                url = item.get("url", "")
                if url and len(url) > 10:
                    lines.append(f"  • {title}")
                    lines.append(f"    🔗 {url[:60]}")
                else:
                    lines.append(f"  • {title}")
        elif coin_price:
            lines.append(f"\n📰 Tidak ada berita terbaru untuk {coin}")
    except Exception as e:
        logger.error(f"News error: {e}")
    
    if has_data and coin_price:
        if coin_price < -1:
            lines.append(f"\n📉 Prediksi: TURUN - tekanan jual")
        elif coin_price > 1:
            lines.append(f"\n📈 Prediksi: NAIK - momentum positif")
        else:
            lines.append(f"\n➡️ Prediksi: SIDEWAYS - tunggu sinyal")
    
    if not has_data and not coin_price:
        lines.append(f"\n⚠️ Kirim foto chart {coin} untuk analisis.")
    
    lines.append("\n_Disclaimer: Bukan financial advice._")
    
    return "\n".join(lines)


def get_quick_market_summary() -> str:
    try:
        overview = get_market_overview()
        
        lines = ["📊 *Market Overview:*\n"]
        
        if overview.get("gainers"):
            lines.append("🔥 *Top Gainers:*")
            for coin, change in overview["gainers"][:3]:
                lines.append(f"  • {coin}: +{change:.2f}%")
        
        if overview.get("losers"):
            lines.append("\n📉 *Top Losers:*")
            for coin, change in overview["losers"][:3]:
                lines.append(f"  • {coin}: {change:.2f}%")
        
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error getting market summary: {e}")
        return "⚠️ Gagal mengambil market overview"


if __name__ == "__main__":
    pred = get_market_prediction("Tren bullish, kekuatan 7/10, RSI 58", "BTC")
    print(format_market_prediction(pred))