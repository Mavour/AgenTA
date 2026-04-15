from data.database import add_journal, get_user_journal, clear_user_journal, get_weekly_stats, update_user


def save_analysis(user_id: int, analysis_text: str, pair: str = None, timeframe: str = None, signal: str = None, price_entry: float = None):
    KNOWN_COINS = ["BTC", "ETH", "SOL", "XRP", "ADA", "BNB", "DOGE", "AVAX", "DOT", "MATIC", "LINK", "UNI", "ATOM", "LTC", "ETC", "XLM", "APT", "ARB", "OP", "NEAR", "FIL", "ALGO", "VET", "HBAR", "ICP", "SAND", "MANA", "AXS", "AAVE", "MKR", "SNX", "CRV", "HYPE", "PEPE", "WIF", "BONK", "MYRO", "SUI", "SEI", "INJ", "TIA", "IMX", "RENDER", "METIS", "RON", "SHIB", "XPL", "BLUR", "WLD", "JTO", "WEN", "BONK", "STX", "LSD", "TIA"]
    
    if pair:
        pair = pair.upper()
        if pair not in KNOWN_COINS:
            pair = "Unknown"
    else:
        pair = "Unknown"
    
    timeframe = timeframe or "Unknown"
    
    signal_lower = None
    if signal:
        signal_lower = signal.lower()
        if "bullish" in signal_lower:
            signal_lower = "bullish"
        elif "bearish" in signal_lower:
            signal_lower = "bearish"
    
    add_journal(user_id, pair, timeframe, analysis_text, signal_lower, price_entry)


def format_journal_list(results: list) -> str:
    if not results:
        return "📔 *Journal kosong*\n\nBelum ada analisis yang disimpan."
    
    lines = ["📔 *Riwayat Analisis*\n"]
    
    for idx, (id_, pair, tf, analysis, signal, price, created) in enumerate(results, 1):
        signal_emoji = ""
        if signal == "bullish":
            signal_emoji = "🟢"
        elif signal == "bearish":
            signal_emoji = "🔴"
        
        truncated = analysis[:80] + "..." if len(analysis) > 80 else analysis
        
        lines.append(f"{idx}. {signal_emoji} *{pair}* ({tf})")
        lines.append(f"   📝 {truncated}")
        lines.append(f"   📅 {created[:10]}")
        lines.append("")
    
    return "\n".join(lines)


def format_weekly_report(user_id: int) -> str:
    stats = get_weekly_stats(user_id)
    
    if not stats:
        return "📊 *Weekly Report*\n\nBelum ada analisis minggu ini."
    
    total = sum(s[0] for s in stats)
    bullish = sum(s[1] for s in stats)
    bearish = sum(s[2] for s in stats)
    
    lines = [
        "📊 *Weekly Report*\n",
        f"📅 Periode: 7 hari terakhir\n",
        f"📈 *Total Analisis:* {total}",
        f"🟢 Bullish: {bullish}",
        f"🔴 Bearish: {bearish}",
        "",
        "📊 *Pasangan Favorit:*",
    ]
    
    for total, bullish, bearish, pair, count in stats:
        lines.append(f"• {pair}: {count}x")
    
    trend = "📈 Bullish" if bullish > bearish else "📉 Bearish" if bearish > bullish else "➡ Sideways"
    lines.extend(["", f"💡 *Trend Minggu Ini:* {trend}"])
    
    return "\n".join(lines)