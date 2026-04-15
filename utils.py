def calculate_rr(entry: float, sl: float, tp: float) -> dict:
    risk = abs(entry - sl)
    reward = abs(tp - entry)

    if risk == 0:
        return {"error": "Entry dan Stop Loss tidak boleh sama"}

    rr_ratio = reward / risk
    risk_percent = (risk / entry) * 100
    reward_percent = (reward / entry) * 100

    if rr_ratio >= 3:
        rating = "Sangat Baik"
    elif rr_ratio >= 2:
        rating = "Baik"
    elif rr_ratio >= 1:
        rating = "Cukup"
    else:
        rating = "Kurang Ideal"

    direction = "LONG" if tp > entry else "SHORT"

    return {
        "direction": direction,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "risk": risk,
        "reward": reward,
        "rr_ratio": round(rr_ratio, 2),
        "risk_percent": round(risk_percent, 2),
        "reward_percent": round(reward_percent, 2),
        "rating": rating,
    }


def format_rr_result(result: dict) -> str:
    if "error" in result:
        return f"❌ Error: {result['error']}"

    return (
        f"📐 *Kalkulator Risk : Reward*\n\n"
        f"📍 Posisi: *{result['direction']}*\n"
        f"🔹 Entry: `{result['entry']}`\n"
        f"🔴 Stop Loss: `{result['sl']}`\n"
        f"🟢 Take Profit: `{result['tp']}`\n\n"
        f"📊 *Risk:* {result['risk_percent']}%\n"
        f"📊 *Reward:* {result['reward_percent']}%\n"
        f"⚖️ *R:R Ratio:* *1 : {result['rr_ratio']}*\n"
        f"⭐ *Rating:* {result['rating']}\n\n"
        f"_Bukan merupakan financial advice. Selalu lakukan riset mandiri (DYOR)._"
    )


def format_error_message(error: str) -> str:
    return (
        f"⚠️ *Terjadi Kesalahan*\n\n"
        f"{error}\n\n"
        f"Jika masalah berlanjut, coba lagi dalam beberapa saat."
    )


def format_welcome() -> str:
    return (
        f"👋 *Selamat datang di Crypto TA Bot!*\n\n"
        f"Saya adalah asisten analisis teknikal yang didukung oleh AI.\n\n"
        f"📸 *Cara Pakai:*\n"
        f"• Kirim *foto chart* → Saya akan analisis teknikal\n"
        f"• Tambahkan *caption* pada foto untuk konteks (contoh: \"BTC/USDT 4H\")\n"
        f"• Kirim *teks biasa* → Saya akan jawab pertanyaan seputar kripto & trading\n\n"
        f"🔄 *Multi-Timeframe:*\n"
        f"Kirim 2 chart berbeda (contoh: chart 4H lalu 1H) dengan pair yang sama\n"
        f"Bot akan otomatis membandingkan analisis kedua timeframe\n\n"
        f"📋 *Command Tersedia:*\n"
        f"• `/help` — Lihat panduan lengkap\n"
        f"• `/rr <entry> <sl> <tp>` — Hitung Risk:Reward ratio\n\n"
        f"🚀 *Silakan kirim foto chart atau ajukan pertanyaan!*"
    )


def format_help() -> str:
    return (
        f"📖 *Panduan Lengkap*\n\n"
        f"🔹 *Analisis Chart*\n"
        f"Kirim foto chart trading Anda. Bot akan menganalisis:\n"
        f"• Tren (bullish/bearish/sideways) + skor kekuatan\n"
        f"• Area Support & Resistance\n"
        f"• Pola candlestick & chart pattern\n"
        f"• Indikator teknikal (RSI, MACD, dll)\n"
        f"• Kesimpulan & level invalidasi\n\n"
        f"💡 *Tips:* Tambahkan caption pada foto untuk konteks lebih baik\n"
        f"Contoh: \"BTC/USDT 4H\" atau \"ETH/USDT 1D - apakah masih bullish?\"\n\n"
        f"🔄 *Multi-Timeframe Comparison*\n"
        f"Cara pakai:\n"
        f"1. Kirim chart pertama (contoh: BTC/4H)\n"
        f"2. Kirim chart kedua dengan pair sama (contoh: BTC/1H)\n"
        f"3. Bot akan otomatis membandingkan & kasih summary\n\n"
        f"Pastikan caption ditulis agar bot tahu timeframe!\n\n"
        f"🔹 *Tanya Jawab*\n"
        f"Kirim teks biasa untuk bertanya seputar:\n"
        f"• Konsep teknikal analysis\n"
        f"• Penjelasan indikator\n"
        f"• Strategi trading\n"
        f"• Istilah kripto & trading\n\n"
        f"🔹 *Kalkulator Risk:Reward*\n"
        f"Gunakan command: `/rr <entry> <sl> <tp>`\n"
        f"Contoh: `/rr 65000 63000 70000`\n\n"
        f"⚠️ *Disclaimer:* Semua analisis bersifat edukatif dan bukan merupakan saran finansial."
    )


def format_analysis_with_keyboard(analysis: str) -> str:
    return analysis


def get_moon_phase(date=None):
    import datetime, math
    
    new_moon_jd = 2451550.1
    synodic_period = 29.530588853
    
    if date is None:
        date = datetime.datetime.now()
    elif isinstance(date, str):
        date = datetime.datetime.fromisoformat(date)
    
    year = date.year
    month = date.month
    day = date.day
    
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    
    jd = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    days_since = (jd - new_moon_jd) % synodic_period
    phase = int(days_since)
    
    phases = [
        ("New Moon", 0),
        ("Waxing Crescent", 1),
        ("First Quarter", 2),
        ("Waxing Gibbous", 3),
        ("Full Moon", 4),
        ("Waning Gibbous", 5),
        ("Last Quarter", 6),
        ("Waning Crescent", 7),
    ]
    
    idx = int(days_since / 3.6913236)
    idx = min(idx, 7)
    name = phases[idx][0]
    
    illumination = math.sin((days_since / synodic_period) * math.pi) ** 2 * 100
    
    if idx == 0:
        timing = "🌓 Favor: Mulai siklus baru / Entry baru"
    elif idx in [1, 2]:
        timing = "🌓 Building: Akumulasi posisi"
    elif idx in [3, 4]:
        timing = "🌕 Peak: Volatility tinggi / Risk tinggi"
    elif idx in [5, 6]:
        timing = "🌗 Koreksi: Evaluasi /ambil profit"
    else:
        timing = "🌘 Penyiapan: Persiapan siklus baru"
    
    return {
        "phase": name,
        "illumination": round(illumination, 1),
        "timing": timing,
        "synodic_day": round(days_since, 1),
    }
