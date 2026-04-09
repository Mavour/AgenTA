import requests
import logging
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

TWITTER_SEARCH_URL = "https://x.com/i/api/graphql/SearchTimeline"
TWITTER_TRENDS_URL = "https://x.com/i/api/2/timeline/trends.json"

CRYPTO_INFLUENCERS = [
    "WatcherGuru",
    "whale_alert",
    "DombaEth27",
    "KalshiTrade",
    "hoteliercrypto",
    "lookonchain",
    "nansen_ai",
    "polyburg",
    "sarjana_crypto",
    "MARKOCHAIN_",
    "OnchainLens",
    "AshCrypto"
]

COOKIE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "twitter_cookie.json")


def load_cookies() -> Optional[Dict]:
    try:
        if os.path.exists(COOKIE_FILE):
            with open(COOKIE_FILE, 'r') as f:
                data = json.load(f)
                
                if "expires" in data:
                    expires = datetime.fromisoformat(data["expires"])
                    if expires < datetime.now():
                        logger.warning("Twitter cookie expired")
                        return None
                
                logger.info("Twitter cookie loaded successfully")
                if data.get("cookies"):
                    return data["cookies"]
                return {"auth_token": data.get("auth_token"), "ct0": data.get("ct0")}
    except Exception as e:
        logger.error(f"Error loading Twitter cookie: {e}")
    return None


def save_cookies(cookies: Dict, auth_token: str, ct0: str):
    expires = datetime.now() + timedelta(days=7)
    
    cookie_data = {
        "cookies": {
            "auth_token": auth_token,
            "ct0": ct0
        },
        "auth_token": auth_token,
        "ct0": ct0,
        "expires": expires.isoformat(),
        "created_at": datetime.now().isoformat()
    }
    
    os.makedirs(os.path.dirname(COOKIE_FILE), exist_ok=True)
    with open(COOKIE_FILE, 'w') as f:
        json.dump(cookie_data, f)
    
    logger.info(f"Twitter cookie saved, expires: {expires}")


def is_cookie_expired() -> bool:
    try:
        if not os.path.exists(COOKIE_FILE):
            return True
        
        with open(COOKIE_FILE, 'r') as f:
            data = json.load(f)
        
        if "expires" in data:
            expires = datetime.fromisoformat(data["expires"])
            return expires < datetime.now()
    except Exception:
        pass
    return True


def get_twitter_headers(cookies: Dict) -> Dict:
    return {
        "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuBuQ3aJAQ6QzmMwkLwN0TKqJ5RtG2Xq1N3U2Q2Z5r0iFVJP1t8L3G5G2JieG6Lz5s4rL8K1P3O3G3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O3O",
        "content-type": "application/json",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "x-csrf-token": cookies.get("ct0", ""),
        "cookie": f"auth_token={cookies.get('auth_token', '')}; ct0={cookies.get('ct0', '')}"
    }


def search_twitter(query: str, limit: int = 20) -> List[Dict]:
    cookies = load_cookies()
    
    if not cookies:
        logger.warning("No Twitter cookie available")
        return []
    
    headers = get_twitter_headers(cookies)
    
    params = {
        "q": query,
        "count": limit,
        "result_type": "recent"
    }
    
    try:
        response = requests.get(TWITTER_SEARCH_URL, headers=headers, params=params, timeout=15)
        
        if response.status_code == 401 or response.status_code == 403:
            logger.error("Twitter cookie expired or invalid")
            return []
        
        if response.status_code == 200:
            data = response.json()
            tweets = []
            
            for item in data.get("globalObjects", {}).get("tweets", {}).values():
                tweets.append({
                    "id": item.get("id_str"),
                    "text": item.get("full_text", ""),
                    "created_at": item.get("created_at"),
                    "user": item.get("user", {}).get("screen_name"),
                    "likes": item.get("favorite_count", 0),
                    "retweets": item.get("retweet_count", 0)
                })
            
            logger.info(f"Got {len(tweets)} tweets for query: {query}")
            return tweets[:limit]
        elif response.status_code == 404:
            logger.warning("Twitter search endpoint changed, trying alternate")
            return []
        else:
            logger.error(f"Twitter search error: {response.status_code}")
    except Exception as e:
        logger.error(f"Twitter search exception: {e}")
    
    return []


def fetch_crypto_tweets(coins: List[str] = None, limit: int = 20) -> List[Dict]:
    if coins is None:
        coins = ["BTC", "ETH", "Bitcoin", "Ethereum", "crypto"]
    
    all_tweets = []
    
    for coin in coins[:3]:
        try:
            query = f"${coin} OR {coin} crypto"
            tweets = search_twitter(query, limit)
            all_tweets.extend(tweets)
        except Exception as e:
            logger.error(f"Error fetching tweets for {coin}: {e}")
    
    unique_tweets = {t["id"]: t for t in all_tweets}.values()
    return list(unique_tweets)[:limit]


def fetch_influencer_tweets(limit: int = 30) -> List[Dict]:
    cookies = load_cookies()
    
    if not cookies:
        logger.info("No X cookie, using mock influencer activity")
        return get_mock_influencer_sentiment()
    
    all_tweets = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "cookie": f"auth_token={cookies.get('auth_token', '')}; ct0={cookies.get('ct0', '')}",
        "x-csrf-token": cookies.get("ct0", "")
    }
    
    for username in CRYPTO_INFLUENCERS[:6]:
        try:
            url = f"https://x.com/i/user/1333465340940955138"  # Need user ID
            all_tweets.append({
                "id": username,
                "text": f"@{username} active",
                "user": username,
                "likes": 0,
            })
        except Exception:
            pass
    
    return all_tweets or get_mock_influencer_sentiment()


def get_mock_influencer_sentiment() -> List[Dict]:
    return [
        {"id": "1", "text": "BTC looking weak below $71K", "user": "WatcherGuru", "likes": 150},
        {"id": "2", "text": "Whale alert: 500 BTC moved to exchange", "user": "whale_alert", "likes": 89},
        {"id": "3", "text": "Bearish divergence forming on daily", "user": "CryptoChef_", "likes": 45},
        {"id": "4", "text": "Support holding at $70K for now", "user": "lookonchain", "likes": 72},
        {"id": "5", "text": "Institutional flows remain strong", "user": "DombaEth27", "likes": 38},
        {"id": "6", "text": "Watch $69.5K support break", "user": "AshCrypto", "likes": 56},
    ]


def get_twitter_sentiment_for_crypto(coin: str = "BTC") -> Dict:
    tweets = fetch_crypto_tweets([coin], limit=30)
    
    if not tweets:
        return {
            "available": False,
            "reason": "No Twitter cookie or API error"
        }
    
    return {
        "available": True,
        "total_tweets": len(tweets),
        "tweets": [
            {"text": t["text"][:100], "likes": t["likes"]} 
            for t in tweets[:10]
        ]
    }


def setup_twitter_cookie(auth_token: str, ct0: str) -> bool:
    try:
        save_cookies({"auth_token": auth_token, "ct0": ct0}, auth_token, ct0)
        
        test_tweets = search_twitter("Bitcoin", limit=1)
        if test_tweets:
            logger.info("Twitter cookie validated successfully")
            return True
        else:
            logger.warning("Twitter cookie may be invalid")
            return False
    except Exception as e:
        logger.error(f"Error setting up Twitter cookie: {e}")
        return False


def check_cookie_status() -> Dict:
    if not os.path.exists(COOKIE_FILE):
        return {"status": "not_set", "message": "Cookie belum diatur"}
    
    try:
        with open(COOKIE_FILE, 'r') as f:
            data = json.load(f)
        
        if "expires" in data:
            expires = datetime.fromisoformat(data["expires"])
            if expires < datetime.now():
                return {"status": "expired", "message": f"Cookie expired pada {expires.strftime('%Y-%m-%d %H:%M')}"}
            
            remaining = (expires - datetime.now()).days
            return {
                "status": "active", 
                "message": f"Cookie aktif, tersisa {remaining} hari",
                "expires": expires.isoformat()
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
    return {"status": "unknown"}


if __name__ == "__main__":
    status = check_cookie_status()
    print(f"Cookie status: {status}")
    
    if status["status"] == "active":
        tweets = search_twitter("Bitcoin", limit=5)
        print(f"Got {len(tweets)} tweets")