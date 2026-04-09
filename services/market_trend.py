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


def format_market_prediction(prediction: Dict) -> str:
    combined = prediction.get("combined", {})
    chart = prediction.get("chart")
    price = prediction.get("price", {})
    news = prediction.get("news")
    twitter = prediction.get("twitter")
    
    lines = ["🎯 *Market Prediction*\n"]
    
    if chart:
        trend_emoji = "🟢" if chart["trend"] == "bullish" else "🔴" if chart["trend"] == "bearish" else "⚪"
        lines.append(f"📈 *Dari Chart:* {trend_emoji} {chart['trend'].title()} (Kekuatan: {chart['strength']}/10)")
    
    if price and price.get("total", 0) > 0:
        gainers = price.get("gainers", 0)
        losers = price.get("losers", 0)
        if losers > gainers:
            lines.append(f"📉 Market: {losers} coin turun vs {gainers} naik")
        elif gainers > losers:
            lines.append(f"📈 Market: {gainers} coin naik vs {losers} turun")
    
    try:
        from services.news_fetcher import fetch_coingecko_news, get_news_with_context
        
        pair = "BTC"
        prices = fetch_coingecko_news(5)
        btc_eth = {}
        for p in prices:
            title = p.get("title", "")
            change = p.get("change_24h", 0)
            if "BTC" in title:
                btc_eth["BTC"] = change
                pair = "BTC"
            elif "ETH" in title:
                btc_eth["ETH"] = change
                pair = "ETH"
        
        ctx = get_news_with_context(coin=pair)
        news_items = ctx.get("rss", [])[:3]
        
        if btc_eth:
            btc = btc_eth.get("BTC", 0)
            eth = btc_eth.get("ETH", 0)
            btc_str = f"{btc:+.2f}%" if btc else "N/A"
            eth_str = f"{eth:+.2f}%" if eth else "N/A"
            sentiment = "bearish" if btc and btc < -1 else "bullish" if btc and btc > 1 else "netral"
            
            if sentiment == "bearish":
                lines.append(f"\n📉 BTC: {btc_str} | ETH: {eth_str}")
                lines.append("⚠️ BTC turun >1% - tekanan jual")
            elif sentiment == "bullish":
                lines.append(f"\n📈 BTC: {btc_str} | ETH: {eth_str}")
                lines.append("✅ BTC naik - momentum positif")
            else:
                lines.append(f"\n💰 BTC: {btc_str} | ETH: {eth_str}")
                lines.append("➡️ BTC netral - tunggu sinyal")
        
        if news_items:
            lines.append(f"\n📰 *Latest:*")
            for item in news_items:
                title = item.get("title", "")[:55]
                lines.append(f"  • {title}")
    except Exception as e:
        logger.error(f"News error: {e}")
    
    if combined:
        sentiment_emoji = "🟢" if combined["sentiment"] == "bullish" else "🔴" if combined["sentiment"] == "bearish" else "⚪"
        lines.append(f"\n🎯 *Kesimpulan Gabungan:*")
        lines.append(f"  {sentiment_emoji} *Prediksi: {combined['sentiment'].upper()}* (Confidence: {combined.get('confidence', 50)}%)")
        
        score = combined.get("score", 0)
        if score > 0.3:
            lines.append("  📊 Sinyal: Positif - Banyak indikator menunjukkan potensi naik")
        elif score < -0.3:
            lines.append("  📊 Sinyal: Negatif - Banyak indikator menunjukkan potensi turun")
        else:
            lines.append("  📊 Sinyal: Netral - Kondisi pasar belum jelas, wait and see")
    
    if not chart and not price:
        lines.append("\n⚠️ Data tidak tersedia. Kirim foto chart untuk analisis.")
    
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