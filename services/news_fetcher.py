import requests
import logging
import feedparser
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

CRYPTO_NEWS_SOURCES = {
    "cryptocompare": "https://min-api.cryptocompare.com/data/v2/news/?lang=EN",
    "coingecko": "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=10&page=1&sparkline=false&price_change_percentage=24h",
    "financialjuice": "https://www.financialjuice.com/feed/"
}


def fetch_cryptocompare_news(limit: int = 10) -> List[Dict]:
    try:
        url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
        params = {"limit": limit}
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            news_data = data.get("Data", [])
            logger.info(f"Got {len(news_data)} news from CryptoCompare")
            return [
                {
                    "title": item.get("title", ""),
                    "source": item.get("source_info", {}).get("name", "Unknown"),
                    "url": item.get("url", ""),
                    "published": item.get("published_on", 0)
                }
                for item in news_data
            ]
    except Exception as e:
        logger.error(f"CryptoCompare error: {e}")
    return []


def fetch_financialjuice_news(limit: int = 10) -> List[Dict]:
    try:
        url = "https://www.financialjuice.com/feed/"
        response = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        if response.status_code == 200:
            feed = feedparser.parse(response.text)
            entries = feed.entries[:limit] if len(feed.entries) >= limit else feed.entries
            
            news_list = []
            for entry in entries:
                news_list.append({
                    "title": entry.get("title", ""),
                    "source": "FinancialJuice",
                    "url": entry.get("link", ""),
                    "published": entry.get("published", "")
                })
            
            logger.info(f"Got {len(news_list)} news from FinancialJuice")
            return news_list
    except Exception as e:
        logger.error(f"FinancialJuice error: {e}")
    return []


def fetch_coingecko_news(limit: int = 10) -> List[Dict]:
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 10,
            "page": 1,
            "sparkline": False
        }
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            news_list = []
            for coin in data[:limit]:
                news_list.append({
                    "title": f"{coin['name']} ({coin['symbol'].upper()}): ${coin['current_price']:,.2f} | 24h: {coin['price_change_percentage_24h']:.2f}%",
                    "source": "CoinGecko",
                    "url": f"https://www.coingecko.com/en/coins/{coin['id']}",
                    "price": coin.get("current_price", 0),
                    "change_24h": coin.get("price_change_percentage_24h", 0)
                })
            logger.info(f"Got {len(news_list)} data from CoinGecko")
            return news_list
    except Exception as e:
        logger.error(f"CoinGecko error: {e}")
    return []


def fetch_all_news(limit: int = 10) -> Dict[str, List[Dict]]:
    all_news = {
        "cryptocompare": fetch_cryptocompare_news(limit),
        "financialjuice": fetch_financialjuice_news(limit),
        "coingecko": fetch_coingecko_news(limit)
    }
    
    total = sum(len(v) for v in all_news.values())
    logger.info(f"Total news fetched: {total}")
    
    return all_news


def get_market_overview() -> Dict:
    try:
        url = "https://min-api.cryptocompare.com/data/pricemulti"
        params = {
            "fsyms": "BTC,ETH,BNB,SOL,XRP,ADA,DOGE,AVAX,DOT,LINK",
            "tsyms": "USD"
        }
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            total_market_cap = 0
            total_volume = 0
            gainers = []
            losers = []
            
            for coin, price_data in data.items():
                usd = price_data.get("USD", {})
                change = usd.get("CHANGE24HOUR", 0)
                
                if change > 0:
                    gainers.append((coin, change))
                elif change < 0:
                    losers.append((coin, change))
            
            gainers.sort(key=lambda x: x[1], reverse=True)
            losers.sort(key=lambda x: x[1])
            
            return {
                "gainers": gainers[:5],
                "losers": losers[:5],
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Market overview error: {e}")
    
    return {"gainers": [], "losers": [], "timestamp": None}


if __name__ == "__main__":
    news = fetch_all_news(5)
    for source, items in news.items():
        print(f"\n{source}: {len(items)} items")