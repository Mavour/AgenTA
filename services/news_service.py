import requests
import logging
import re

logger = logging.getLogger(__name__)


def fetch_crypto_news(limit: int = 10):
    try:
        url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
        params = {"limit": limit}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            news_data = data.get("Data", [])
            if news_data:
                return news_data
    except Exception as e:
        logger.error(f"News API error: {e}")
    
    return fetch_news_fallback(limit)


def fetch_news_fallback(limit: int = 10):
    try:
        import feedparser
        feeds = [
            "https://cointelegraph.com/rss",
            "https://www.coindesk.com/arc/outboundfeeds/rss/"
        ]
        news = []
        for feed_url in feeds:
            try:
                response = requests.get(feed_url, timeout=8)
                if response.status_code == 200:
                    feed = feedparser.parse(response.text)
                    for entry in feed.entries[:limit // 2]:
                        news.append({
                            "title": entry.get("title", "No title")[:70],
                            "source_info": {"name": "Cointelegraph/Coindesk"},
                            "url": entry.get("link", "")
                        })
                        if len(news) >= limit:
                            break
            except Exception as e:
                logger.error(f"RSS feed error: {e}")
        return news
    except Exception as e:
        logger.error(f"Fallback news error: {e}")
    
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
        response = requests.get(url, params=params, timeout=15)
        logger.info(f"Price API response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Got prices for {len(data)} coins")
            lines = ["💰 *Harga Crypto Terkini:*\n"]
            
            for coin, price in data.items():
                usd = price.get("USD", 0)
                lines.append(f"• {coin}: ${usd:,.2f}")
            
            return "\n".join(lines)
    except Exception as e:
        logger.error(f"Price API error: {e}")
    
    return fetch_prices_fallback()


def fetch_prices_fallback():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": "bitcoin,ethereum,solana,ripple,cardano,dogecoin",
            "vs_currencies": "usd"
        }
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            coin_map = {
                "bitcoin": "BTC",
                "ethereum": "ETH", 
                "solana": "SOL",
                "ripple": "XRP",
                "cardano": "ADA",
                "dogecoin": "DOGE"
            }
            lines = ["💰 *Harga Crypto Terkini:*\n"]
            for coin_id, ticker in coin_map.items():
                if coin_id in data:
                    usd = data[coin_id]["usd"]
                    lines.append(f"• {ticker}: ${usd:,.2f}")
            return "\n".join(lines)
    except Exception as e:
        logger.error(f"Fallback price API error: {e}")
    
    return None


def get_open_interest(pair: str = "BTC") -> dict:
    try:
        pair_id = pair.upper()
        coin_map = {
            "BTC": "bitcoin",
            "ETH": "ethereum", 
            "SOL": "solana",
            "XRP": "ripple",
            "ADA": "cardano",
            "DOGE": "dogecoin",
            "HYPE": "hyper-v2",
            "PEPE": "pepe",
            "WIF": "wif",
            "BONK": "bonk"
        }
        
        coin_id = coin_map.get(pair_id, pair_id.lower())
        
        url = f"https://api.coinmarketcap.com/api/v3/coins/{coin_id}/market-data"
        params = {"quote": "usd"}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            oi = data.get("data", {}).get("open_interest")
            if oi:
                return {
                    "open_interest": oi,
                    "source": "CoinMarketCap"
                }
    except Exception as e:
        logger.error(f"Open Interest API error: {e}")
    
    try:
        url = f"https://api.jup.ag/open-interest/v1/{pair.upper()}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            oi = data.get("open_interest")
            if oi:
                return {
                    "open_interest": float(oi),
                    "source": "Jupiter"
                }
    except Exception as e:
        logger.error(f"Jupiter OI error: {e}")
    
    return None