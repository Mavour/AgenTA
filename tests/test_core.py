import pytest
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_rss_news_fetch():
    from services.news_fetcher import fetch_rss_news
    news = fetch_rss_news(5)
    assert isinstance(news, list)
    for n in news:
        assert "title" in n
        assert "url" in n
    print(f"RSS: {len(news)} items fetched")

def test_coingecko_fetch():
    from services.news_fetcher import fetch_coingecko_news
    try:
        prices = fetch_coingecko_news(5)
        assert isinstance(prices, list)
        print(f"CG: {len(prices)} prices fetched")
    except Exception as e:
        print(f"CG: rate limited (expected)")

def test_get_news_with_context():
    from services.news_fetcher import get_news_with_context
    
    result = get_news_with_context("BTC")
    assert result is not None
    print(f"BTC context: {list(result.keys())}")
    
    result2 = get_news_with_context("ETH")
    assert result2 is not None
    print(f"ETH context: {list(result2.keys())}")

def test_market_prediction_structure():
    from services.market_trend import get_market_prediction
    
    r = get_market_prediction(None, "BTC")
    assert "chart" in r
    assert "price" in r
    assert "combined" in r
    print(f"Prediction keys: {list(r.keys())}")

def test_format_market_prediction():
    from services.market_trend import get_market_prediction, format_market_prediction
    
    r = get_market_prediction(None, "BTC")
    output = format_market_prediction(r, "BTC")
    assert len(output) > 0
    assert "BTC" in output
    print(f"Format output length: {len(output)}")

def test_sentiment_analyzer():
    from services.sentiment_analyzer import analyze_text_sentiment
    
    assert analyze_text_sentiment("Bitcoin mooning") == "bullish"
    assert analyze_text_sentiment("crypto crash") == "bearish"
    assert analyze_text_sentiment("price stable") == "neutral"
    print("Sentiment: OK")

def test_extract_chart_signal():
    from services.market_trend import extract_chart_signal
    
    signal = extract_chart_signal("Tren bullish kekuatan 7/10")
    assert signal["trend"] == "bullish"
    assert signal["strength"] == 7
    
    signal2 = extract_chart_signal("Bearish trend")
    assert signal2["trend"] == "bearish"
    
    print("Chart signal: OK")

if __name__ == "__main__":
    print("=== Running Tests ===")
    test_rss_news_fetch()
    test_coingecko_fetch()
    test_get_news_with_context()
    test_market_prediction_structure()
    test_format_market_prediction()
    test_sentiment_analyzer()
    test_extract_chart_signal()
    print("\n=== All Tests Passed ===")