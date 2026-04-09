import requests
import logging
import feedparser
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

RSS_FEEDS = {
    "cointelegraph": "https://cointelegraph.com/rss",
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "cointelegraph_markets": "https://cointelegraph.com/rss/tag/markets",
    "cointelegraph_bitcoin": "https://cointelegraph.com/rss/tag/bitcoin",
    "cointelegraph_ethereum": "https://cointelegraph.com/rss/tag/ethereum",
}

MOCK_NEWS = []
CRYPTO_NEWS_SOURCES = {
    "cryptocompare": "https://min-api.cryptocompare.com/data/v2/news/?lang=EN",
    "coingecko": "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=20&page=1&sparkline=false&price_change_percentage=24h",
}


def fetch_rss_news(limit: int = 10) -> List[Dict]:
    news_list = []
    for feed_name, feed_url in RSS_FEEDS.items():
        try:
            response = requests.get(feed_url, timeout=10, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            if response.status_code == 200:
                feed = feedparser.parse(response.text)
                for entry in feed.entries[:limit // len(RSS_FEEDS)]:
                    news_list.append({
                        "title": entry.get("title", ""),
                        "source": feed_name.replace("cointelegraph_", "").title(),
                        "url": entry.get("link", ""),
                        "published": entry.get("published", "")
                    })
        except Exception as e:
            logger.error(f"RSS feed error {feed_name}: {e}")
    return news_list[:limit]


def get_news_with_context(coin: str = None) -> Dict:
    rss_news = fetch_rss_news(limit=15)
    
    if coin and rss_news:
        coin_upper = coin.upper()
        filtered = [n for n in rss_news if coin_upper in n.get("title", "").upper()]
        if filtered:
            return {"rss": filtered}
    
    if rss_news:
        return {"rss": rss_news}
    
    logger.warning("All news sources failed, using mock data")
    return {"mock": []}


MOCK_NEWS = [
    {"title": "Bitcoin surges past $71K as institutional investors increase positions", "source": "CoinDesk"},
    {"title": "Ethereum ETF inflows hit new weekly record", "source": "Bloomberg"},
    {"title": "Crypto market cap reaches $2.4 trillion", "source": "CoinMarketCap"},
    {"title": "Bitcoin whale moves 10,000 BTC to cold wallet", "source": "Decrypt"},
    {"title": "DeFi total value locked surpasses $100 billion", "source": "DeFi Pulse"},
    {"title": "SEC delays decision on Ethereum ETF options", "source": "Reuters"},
    {"title": "Bitcoin mining difficulty reaches new all-time high", "source": "BTC.com"},
    {"title": "Solana network sees record transaction volume", "source": "Solana Foundation"},
    {"title": "Regulatory concerns weigh on crypto market sentiment", "source": "Financial Times"},
    {"title": "Crypto exchange listings surge in Q2", "source": "The Block"},
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
    
    gainers_data = []
    losers_data = []
    for c in coins_data:
        title = c.get("title", "")
        symbol = title.split("(")[1].split(")")[0] if "(" in title else title.split(":")[0].strip()
        change = c.get("change_24h", 0)
        if change > 0:
            gainers_data.append((symbol, change))
        elif change < 0:
            losers_data.append((symbol, change))
    
    gainers_data.sort(key=lambda x: x[1], reverse=True)
    losers_data.sort(key=lambda x: x[1])
    
    gainers = len(gainers_data)
    losers = len(losers_data)
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
        "losers_pct": round((losers/total)*100, 1) if total > 0 else 0,
        "top_gainers": [g[0] for g in gainers_data[:3]],
        "top_losers": [l[0] for l in losers_data[:3]]
    }


def fetch_all_news(limit: int = 10) -> Dict[str, List[Dict]]:
    rss_news = get_news_with_context()
    
    if rss_news.get("rss"):
        return rss_news
    
    cg_news = fetch_coingecko_news(limit)
    
    if not cg_news:
        logger.warning("All news APIs failed, using fallback")
        return {"mock": []}
    
    all_news = {
        "coingecko": cg_news
    }
    
    total = sum(len(v) for v in all_news.values())
    logger.info(f"Total news fetched: {total}")
    
    if total == 0:
        return {"mock": []}
    
    return all_news
    
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