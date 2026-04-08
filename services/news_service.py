import requests
import re
from datetime import datetime, timedelta


def fetch_crypto_news(limit: int = 10):
    try:
        url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
        params = {"limit": limit}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("Data", [])
    except Exception:
        pass
    
    return []


def analyze_sentiment(text: str) -> str:
    text_lower = text.lower()
    
    bullish_words = ["bullish", "surge", "rally", "gain", "rise", "up", "positive", "growth", "breakout", "moon", " ATH"]
    bearish_words = ["bearish", "crash", "drop", "fall", "down", "negative", " decline", "sell", "dump", "breakdown"]
    
    bullish_count = sum(1 for word in bullish_words if word in text_lower)
    bearish_count = sum(1 for word in bearish_words if word in text_lower)
    
    if bullish_count > bearish_count:
        return "bullish"
    elif bearish_count > bullish_count:
        return "bearish"
    return "neutral"


def format_news_response(news_list: list, pair: str = None) -> str:
    if not news_list:
        return "⚠️ Tidak dapat mengambil berita. Coba lagi nanti."
    
    lines = ["📰 *Crypto News"
]
    
    if pair:
        lines[0] += f" - {pair.upper()}"
    lines.append("")
    
    bullish_count = 0
    bearish_count = 0
    neutral_count = 0
    
    for idx, news in enumerate(news_list[:8], 1):
        title = news.get("title", "No title")[:60]
        source = news.get("source_info", {}).get("name", "Unknown")
        url = news.get("url", "")
        
        sentiment = analyze_sentiment(title)
        
        if sentiment == "bullish":
            emoji = "🟢"
            bullish_count += 1
        elif sentiment == "bearish":
            emoji = "🔴"
            bearish_count += 1
        else:
            emoji = "⚪"
            neutral_count += 1
        
        lines.append(f"{idx}. {emoji} *{title}*")
        lines.append(f"   📰 {source}")
        lines.append("")
    
    lines.append("📊 *Sentiment Overview:*")
    lines.append(f"🟢 Bullish: {bullish_count}")
    lines.append(f"🔴 Bearish: {bearish_count}")
    lines.append(f"⚪ Neutral: {neutral_count}")
    
    if bullish_count > bearish_count:
        overall = "🟢 *Overall: Bullish*"
    elif bearish_count > bullish_count:
        overall = "🔴 *Overall: Bearish*"
    else:
        overall = "⚪ *Overall: Neutral*"
    lines.append(overall)
    
    lines.append("")
    lines.append("_Bukan merupakan financial advice._")
    
    return "\n".join(lines)


def get_crypto_prices():
    try:
        url = "https://min-api.cryptocompare.com/data/pricemulti"
        params = {
            "fsyms": "BTC,ETH,SOL,XRP,ADA,DOGE",
            "tsyms": "USD"
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            lines = ["💰 *Harga Crypto Terkini:*\n"]
            
            for coin, price in data.items():
                usd = price.get("USD", 0)
                lines.append(f"• {coin}: ${usd:,.2f}")
            
            return "\n".join(lines)
    except Exception:
        pass
    
    return None