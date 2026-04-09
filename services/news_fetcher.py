import requests
import logging
import feedparser
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

MOCK_NEWS = [
    {"title": "Bitcoin surges past $71K as institutional investors increase positions", "source": "CoinDesk", "url": "https://coindesk.com"},
    {"title": "Ethereum ETF inflows hit new weekly record", "source": "Bloomberg", "url": "https://bloomberg.com"},
    {"title": "Crypto market cap reaches $2.4 trillion", "source": "CoinMarketCap", "url": "https://coinmarketcap.com"},
    {"title": "Bitcoin whale moves 10,000 BTC to cold wallet", "source": "Decrypt", "url": "https://decrypt.co"},
    {"title": "DeFi total value locked surpasses $100 billion", "source": "DeFi Pulse", "url": "https://defipulse.com"},
    {"title": "SEC delays decision on Ethereum ETF options", "source": "Reuters", "url": "https://reuters.com"},
    {"title": "Bitcoin mining difficulty reaches new all-time high", "source": "BTC.com", "url": "https://btc.com"},
    {"title": "Solana network sees record transaction volume", "source": "Solana Foundation", "url": "https://solana.com"},
    {"title": "Regulatory concerns weigh on crypto market sentiment", "source": "Financial Times", "url": "https://ft.com"},
    {"title": "Crypto exchange listings surge in Q2", "source": "The Block", "url": "https://theblock.co"},
]

CRYPTO_NEWS_SOURCES = {
    "cryptocompare": "https://min-api.cryptocompare.com/data/v2/news/?lang=EN",
    "coingecko": "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=20&page=1&sparkline=false&price_change_percentage=24h",
}


def fetch_cryptocompare_news(limit: int = 10) -> List[Dict]:
    try:
        url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
        params = {"limit": limit}
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("Response") == "Success":
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


def fetch_coingecko_news(limit: int = 20) -> List[Dict]:
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": limit,
            "page": 1,
            "sparkline": False
        }
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 429:
            logger.warning("CoinGecko rate limited, using fallback")
            return fetch_cmc_prices(limit)
        
        if response.status_code == 200:
            data = response.json()
            news_list = []
            gainers = []
            losers = []
            
            for coin in data[:limit]:
                change = coin.get("price_change_percentage_24h", 0)
                news_list.append({
                    "title": f"{coin['name']} ({coin['symbol'].upper()}): ${coin['current_price']:,.2f} | 24h: {change:.2f}%",
                    "source": "CoinGecko",
                    "url": f"https://www.coingecko.com/en/coins/{coin['id']}",
                    "price": coin.get("current_price", 0),
                    "change_24h": change
                })
                
                if change > 0:
                    gainers.append(coin['symbol'].upper())
                elif change < 0:
                    losers.append(coin['symbol'].upper())
            
            logger.info(f"Got {len(news_list)} data from CoinGecko - {len(gainers)} gainers, {len(losers)} losers")
            return news_list
    except Exception as e:
        logger.error(f"CoinGecko error: {e}")
        return fetch_cmc_prices(limit)


def fetch_cmc_prices(limit: int = 20) -> List[Dict]:
    """Fallback using CoinMarketCap free API or mock data"""
    try:
        url = "https://api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
        params = {"limit": limit, "convert": "USD"}
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            news_list = []
            gainers = []
            losers = []
            
            for coin in data.get("data", [])[:limit]:
                change = coin.get("percent_change_24h", 0)
                news_list.append({
                    "title": f"{coin['name']} ({coin['symbol']}): ${coin.get('quote', {}).get('USD', {}).get('price', 0):,.2f} | 24h: {change:.2f}%",
                    "source": "CoinMarketCap",
                    "url": f"https://coinmarketcap.com/currencies/{coin['slug']}/",
                    "price": coin.get("quote", {}).get("USD", {}).get("price", 0),
                    "change_24h": change
                })
                
                if change > 0:
                    gainers.append(coin['symbol'])
                elif change < 0:
                    losers.append(coin['symbol'])
            
            logger.info(f"Got {len(news_list)} data from CoinMarketCap")
            return news_list
    except Exception as e:
        logger.error(f"CMC error: {e}")
    
    return get_mock_price_data(limit)


def get_mock_price_data(limit: int = 20) -> List[Dict]:
    """Mock data when all APIs fail"""
    mock_coins = [
        {"name": "Bitcoin", "symbol": "BTC", "price": 70000, "change_24h": -1.2},
        {"name": "Ethereum", "symbol": "ETH", "price": 2200, "change_24h": -2.5},
        {"name": "BNB", "symbol": "BNB", "price": 600, "change_24h": -2.8},
        {"name": "Solana", "symbol": "SOL", "price": 140, "change_24h": 1.5},
        {"name": "XRP", "symbol": "XRP", "price": 1.3, "change_24h": -3.2},
        {"name": "Cardano", "symbol": "ADA", "price": 0.45, "change_24h": -1.8},
        {"name": "Dogecoin", "symbol": "DOGE", "price": 0.15, "change_24h": 2.1},
        {"name": "Avalanche", "symbol": "AVAX", "price": 35, "change_24h": -0.5},
        {"name": "Polkadot", "symbol": "DOT", "price": 7.5, "change_24h": -1.1},
        {"name": "Chainlink", "symbol": "LINK", "price": 15, "change_24h": 0.8},
    ]
    
    news_list = []
    gainers = []
    losers = []
    
    for coin in mock_coins[:limit]:
        change = coin["change_24h"]
        news_list.append({
            "title": f"{coin['name']} ({coin['symbol']}): ${coin['price']:,.2f} | 24h: {change:.2f}%",
            "source": "Mock Data (API Unavailable)",
            "url": "#",
            "price": coin["price"],
            "change_24h": change
        })
        
        if change > 0:
            gainers.append(coin['symbol'])
        elif change < 0:
            losers.append(coin['symbol'])
    
    return news_list


def get_market_sentiment_from_prices() -> Dict:
    """Analyze sentiment based on price changes of top coins"""
    coins_data = fetch_coingecko_news(20)
    
    if not coins_data:
        return {"sentiment": "neutral", "gainers": 0, "losers": 0, "total": 0}
    
    gainers = sum(1 for c in coins_data if c.get("change_24h", 0) > 0)
    losers = sum(1 for c in coins_data if c.get("change_24h", 0) < 0)
    total = len(coins_data)
    
    if gainers > losers + 3:
        sentiment = "bullish"
    elif losers > gainers + 3:
        sentiment = "bearish"
    else:
        sentiment = "neutral"
    
    return {
        "sentiment": sentiment,
        "gainers": gainers,
        "losers": losers,
        "total": total,
        "gainers_pct": round((gainers/total)*100, 1) if total > 0 else 0,
        "losers_pct": round((losers/total)*100, 1) if total > 0 else 0
    }


def fetch_all_news(limit: int = 10) -> Dict[str, List[Dict]]:
    cg_news = fetch_coingecko_news(limit)
    
    if not cg_news:
        logger.warning("CoinGecko API failed, using mock data")
        return {"mock": MOCK_NEWS[:limit]}
    
    all_news = {
        "coingecko": cg_news
    }
    
    total = sum(len(v) for v in all_news.values())
    logger.info(f"Total news fetched: {total}")
    
    if total == 0:
        return {"mock": MOCK_NEWS[:limit]}
    
    return all_news


def get_market_overview() -> Dict:
    try:
        price_data = fetch_coingecko_news(20)
        
        gainers = []
        losers = []
        
        for coin in price_data:
            change = coin.get("change_24h", 0)
            symbol = coin.get("title", "?").split(":")[0].strip()
            
            if change > 0:
                gainers.append((symbol, change))
            elif change < 0:
                losers.append((symbol, change))
        
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