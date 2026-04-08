import re


def parse_timeframe(text: str) -> list:
    tf_patterns = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "MN"]
    
    text_lower = text.lower()
    found_tfs = []
    
    for tf in tf_patterns:
        if tf in text_lower:
            found_tfs.append(tf)
    
    if not found_tfs:
        return ["1h"]
    
    return found_tfs


def format_multi_tf_response(analyses: dict) -> str:
    if not analyses:
        return "⚠️ Gagal menganalisis timeframe."
    
    lines = ["📊 *Analisis Multi Timeframe*\n"]
    
    for tf, analysis in analyses.items():
        lines.append(f"--- *{tf.upper()}* ---")
        
        analysis_lower = analysis.lower()
        
        if "bullish" in analysis_lower:
            signal = "🟢 Bullish"
        elif "bearish" in analysis_lower:
            signal = "🔴 Bearish"
        else:
            signal = "⚪ Sideways"
        
        lines.append(f"Signal: {signal}")
        
        trend_match = re.search(r"(tren|trend)[:\s]+(\w+)", analysis_lower)
        if trend_match:
            lines.append(f"Tren: {trend_match.group(2).title()}")
        
        sr_match = re.search(r"(support|resistance)[:\s]*(\d+[,.]?\d*)", analysis_lower)
        if sr_match:
            lines.append(f"{sr_match.group(1).title()}: ${sr_match.group(2)}")
        
        lines.append("")
    
    lines.append("💡 *Kesimpulan:*")
    
    bullish_count = sum(1 for a in analyses.values() if "bullish" in a.lower())
    bearish_count = sum(1 for a in analyses.values() if "bearish" in a.lower())
    
    if bullish_count > bearish_count:
        lines.append("🟢 *Overall: Bullish* - Lebih banyak timeframe menunjukkan uptrend")
    elif bearish_count > bullish_count:
        lines.append("🔴 *Overall: Bearish* - Lebih banyak timeframe menunjukkan downtrend")
    else:
        lines.append("⚪ *Overall: Mixed* - Waktu berbeda menunjukkan arah berbeda")
    
    lines.append("")
    lines.append("_Bukan merupakan financial advice._")
    
    return "\n".join(lines)


def prepare_multi_tf_prompt(base_prompt: str, timeframe: str) -> str:
    return f"{base_prompt}\n\nFokus analisis pada timeframe {timeframe.upper()}. Berikan analisis yang spesifik untuk timeframe ini."