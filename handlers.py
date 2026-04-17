import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from openrouter_client import analyze_chart, answer_question, OpenRouterError, RateLimitError
from utils import (
    calculate_rr,
    format_rr_result,
    format_error_message,
    format_welcome,
    format_help,
    get_moon_phase,
)
from data.journal import save_analysis, format_journal_list, format_weekly_report
from services.news_service import fetch_crypto_news, format_news_response, get_crypto_prices
from services.market_trend import get_market_prediction, format_market_prediction, get_quick_market_summary
from data.cookie_manager import check_twitter_cookie

logger = logging.getLogger(__name__)

TREND_TRIGGER_PATTERNS = [
    "naik", "turun", "bull", "bear", "market", "trend", "prediction",
    "akan naik", "akan turun", "kemungkinan", "kesimpulan", "prediksi",
    "arah market", "arah harga", "kesempatan buy", "kesempatan sell",
    "bullish", "bearish", "sentiment", "bagaimana pasar", "kondisi pasar",
    "mau naik", "mau turun", "sekarang", "ini bullish", "ini bearish"
]

MENU_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📊 Analisis Chart"), KeyboardButton("💬 Tanya Jawab")],
        [KeyboardButton("📔 Journal"), KeyboardButton("📰 News")],
        [KeyboardButton("💰 Harga"), KeyboardButton("📊 Report")],
        [KeyboardButton("📖 Panduan")],
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
)

photo_cache = {}
photo_cache_2 = {}
multi_tf_cache = {}
last_analysis_cache = {}
last_analysis_text_cache = {}


async def _send_md(message, text, **kwargs):
    try:
        return await message.reply_text(text, parse_mode="Markdown", **kwargs)
    except BadRequest:
        return await message.reply_text(text, **kwargs)


async def _edit_text_msg(message, text, **kwargs):
    try:
        return await message.edit_text(text, parse_mode="Markdown", **kwargs)
    except BadRequest:
        return await message.edit_text(text, **kwargs)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        format_welcome(),
        parse_mode="Markdown",
        reply_markup=MENU_KEYBOARD,
    )


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *Menu Utama*",
        parse_mode="Markdown",
        reply_markup=MENU_KEYBOARD,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        format_help(),
        parse_mode="Markdown",
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        return

    await update.message.chat.send_action(action="typing")

    status_msg = await update.message.reply_text(
        "⏳ *Menganalisis & membuat visualisasi...*\n\nMohon tunggu sebentar.",
        parse_mode="Markdown"
    )

    photo = update.message.photo[-1]
    caption = update.message.caption or ""
    user_id = update.message.from_user.id

    try:
        file = await photo.get_file()
        image_bytes = await file.download_as_bytearray()
        image_bytes = bytes(image_bytes)

        from openrouter_client import _check_image_quality
        quality = _check_image_quality(image_bytes)
        if quality["quality"] != "ok":
            await status_msg.edit_text(
                f"⚠️ *Gambar Jelek*\n\n{quality['reason']}\n\nSilakan kirim foto chart yang lebih jelas.",
                parse_mode="Markdown"
            )
            return

        pair, tf = "BTC", "Unknown"
        
        if caption:
            import re
            pair_match = re.search(r"([A-Z]{2,10})(?:/|\s)", caption.upper())
            if pair_match:
                pair = pair_match.group(1)
            
            tf_match = re.search(r"(\d+[mMdDhH])", caption)
            if tf_match:
                tf = tf_match.group(1).upper()
        
        photo_cache[user_id] = (image_bytes, caption, tf)
        last_analysis_cache[user_id] = "chart"
        
        multi_key = f"{user_id}_{pair}"
        
        if multi_key in multi_tf_cache and multi_tf_cache[multi_key]:
            img1, tf1, cap1 = multi_tf_cache[multi_key]
            await _handle_multi_tf(update, status_msg, img1, image_bytes, pair, tf1, tf, cap1, caption)
            return
        
        multi_tf_cache[multi_key] = (image_bytes, tf, caption)
        
        if len(multi_tf_cache) > 50:
            oldest = list(multi_tf_cache.keys())[0]
            del multi_tf_cache[oldest]
        
        hint_msg = f"📊 Chart {pair} {tf} diterima! 📨 Kirim chart timeframe lain (contoh: 1H) untuk comparação.\n\nKetik /compare untuk melihat comparison terbaru."
        
        context = f"Analisis chart {pair} TF {tf}" + (f" - {caption}" if caption else "")
        analysis = await analyze_chart(image_bytes, context, pair)
        last_analysis_text_cache[user_id] = analysis

        signal = None
        analysis_lower = analysis.lower()
        bullish_keywords = ["buy", "long", "naik", "bullish", "entry", "tp ", "take profit", "beli", "call"]
        bearish_keywords = ["sell", "short", "turun", "bearish", "sl ", "stop loss", "jual", "put"]
        
        bullish_count = sum(1 for kw in bullish_keywords if kw in analysis_lower)
        bearish_count = sum(1 for kw in bearish_keywords if kw in analysis_lower)
        
        if bullish_count > bearish_count:
            signal = "bullish"
        elif bearish_count > bullish_count:
            signal = "bearish"
        
        save_analysis(user_id, analysis, pair=pair, timeframe=tf, signal=signal)

        hint_msg = f"\n\n💡 _Kirim chart timeframe lain ({'1H' if tf in ['4H','D'] else '4H' if tf in ['1H','D'] else '1D'}) untuk comparison._"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Analisis Ulang", callback_data="retry_analysis"), InlineKeyboardButton("📄 PDF", callback_data="export_pdf")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await status_msg.edit_text(analysis + hint_msg, parse_mode="Markdown", reply_markup=reply_markup)

    except Exception as e:
        logger.exception("Error in photo handler: %s", type(e).__name__)
        try:
            await status_msg.edit_text(
                format_error_message("Terjadi kesalahan saat memproses gambar."),
                parse_mode="Markdown"
            )
        except Exception:
            pass


async def _handle_multi_tf(update, status_msg, img1_bytes, img2_bytes, pair, tf1, tf2, caption1, caption2):
    await status_msg.edit_text(f"🔄 *Membandingkan {tf1} vs {tf2}...*", parse_mode="Markdown")
    
    analysis1 = await analyze_chart(img1_bytes, f"Chart {pair} TF {tf1} - {caption1}", pair)
    analysis2 = await analyze_chart(img2_bytes, f"Chart {pair} TF {tf2} - {caption2}", pair)
    
    lines = [
        f"📊 *Multi-Timeframe Analysis: {pair}*\n",
        f"┌{'─'*20}┬{'─'*20}┐",
        f"│ {tf1:<18} │ {tf2:<18} │",
        f"├{'─'*20}┼{'─'*20}┤",
    ]
    
    for line in analysis1.split('\n'):
        if 'TREND' in line.upper():
            lines.append(f"│ {line[:18]:<18} │")
            break
    
    for line in analysis2.split('\n'):
        if 'TREND' in line.upper():
            lines[lines.index(lines[-1])] = f"│ {lines[-1][:20]:<18} │ {line[:18]:<18} │"
            break
    
    lines.append(f"└{'─'*20}┴{'─'*20}┘")
    lines.append("")
    lines.append(f"📈 *Summary:*")
    
    if "bullish" in analysis1.lower() and "bullish" in analysis2.lower():
        lines.append("🟢 Konfirmasi Bullish di kedua timeframe")
    elif "bearish" in analysis1.lower() and "bearish" in analysis2.lower():
        lines.append("🔴 Konfirmasi Bearish di kedua timeframe")
    else:
        lines.append("⚠️ Konflik sinyal - berhati-hati")
    
    lines.append("")
    lines.append("_Bukan financial advice._")
    
    await status_msg.edit_text("\n".join(lines), parse_mode="Markdown")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip() if update.message.text else ""
    await _handle_qa_with_context(update, text)


async def _handle_qa_with_context(update: Update, text: str):
    user_id = update.message.from_user.id
    
    pair = "BTC"
    if user_id in photo_cache:
        _, caption, _ = photo_cache[user_id]
        pair = caption.split()[0].upper() if caption else "BTC"
    
    context_hint = ""
    last_analysis = last_analysis_cache.get(user_id, "")
    last_text = last_analysis_text_cache.get(user_id, "")
    
    if last_analysis == "chart" and last_text:
        truncated_text = last_text[:500] if len(last_text) > 500 else last_text
        context_hint = f"Analisis chart: {truncated_text}\n\n"
    
    status_msg = await update.message.reply_text(
        "⏳ *Sedang memproses...*",
        parse_mode="Markdown"
    )
    
    try:
        from services.news_fetcher import fetch_coingecko_news
        
        prices = fetch_coingecko_news(2, use_cache=True)
        btc = eth = "N/A"
        for p in prices:
            title = p.get("title", "")
            chg = p.get("change_24h", 0)
            if "BTC" in title.upper():
                btc = f"{chg:+.2f}%" if chg else "N/A"
            elif "ETH" in title.upper():
                eth = f"{chg:+.2f}%" if chg else "N/A"
        
        price_ctx = f"BTC: {btc}, ETH: {eth}" if btc != "N/A" else "Data tidak tersedia"
        chart_ctx = truncated_text[:300] if last_analysis == "chart" else ""
        
        lower = text.lower()
        
        if last_analysis == "chart" and last_text:
            if "jual" in lower or "sell" in lower or "beli" in lower or "buy" in lower:
                await status_msg.edit_text(
                    f"📊 * analisis chart:*\n\n{truncated_text[:400]}...\n\n"
                    f"📉 *Kesimpulan:* Trend Bearish, Kekuatan 7/10\n"
                    f"👉 SELL: Di harga sekarang, SL: {truncated_text.split('Stop Loss')[1].split('$')[1].split()[0] if 'Stop Loss' in truncated_text else 'di atas'}\n"
                    f"❌ BUY: Belum disarankan (bearish)",
                    parse_mode="Markdown"
                )
                return
        
        response = await answer_question(full_text, None)
        
        last_analysis_cache[user_id] = "text"
        await status_msg.edit_text(response, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error processing question: {type(e).__name__}: {e}")
        try:
            await status_msg.edit_text(
                format_error_message(f"Terjadi kesalahan: {type(e).__name__}"),
                parse_mode="Markdown"
            )
        except Exception:
            pass


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "retry_analysis":
        await _edit_text_msg(query.message, "🔄 Menganalisis ulang...")
        await query.message.chat.send_action(action="typing")

        user_id = query.from_user.id

        try:
            msg = query.message
            image_bytes = None
            caption = ""

            if msg.reply_to_message and msg.reply_to_message.photo:
                photo = msg.reply_to_message.photo[-1]
                caption = msg.reply_to_message.caption or ""
                file = await photo.get_file()
                image_bytes = await file.download_as_bytearray()
                image_bytes = bytes(image_bytes)
            elif user_id in photo_cache:
                image_bytes, caption, _ = photo_cache[user_id]

            if image_bytes:
                analysis = await analyze_chart(image_bytes, caption, pair)

                keyboard = [
                    [InlineKeyboardButton("🔄 Analisis Ulang", callback_data="retry_analysis"), InlineKeyboardButton("📄 PDF", callback_data="export_pdf")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await _edit_text_msg(query.message, analysis, reply_markup=reply_markup)
            else:
                await _edit_text_msg(query.message, "⚠️ Tidak dapat menemukan foto. Silakan kirim ulang foto chart.")

        except Exception as e:
            logger.exception("Error in retry handler")
            try:
                await _edit_text_msg(query.message, format_error_message("Terjadi kesalahan saat analisis ulang."))
            except Exception:
                pass

    elif query.data == "export_pdf":
        await query.answer("Membuat PDF...", show_alert=True)
        
        user_id = query.from_user.id
        
        try:
            analysis_text = None
            pair = "Unknown"
            
            if user_id in last_analysis_text_cache:
                analysis_text = last_analysis_text_cache[user_id]
                if user_id in photo_cache:
                    _, caption, _ = photo_cache[user_id]
                    pair = caption.split()[0] if caption else "Unknown"
            else:
                from data.database import get_user_journal
                results = get_user_journal(user_id, limit=1)
                if results:
                    _, pair, _, analysis_text, _, _, _ = results[0]
            
            if analysis_text:
                from data.export_pdf import generate_pdf_file
                filename = generate_pdf_file(analysis_text, pair=pair)
                
                await query.message.reply_document(document=open(filename, "rb"))
                
                import os
                os.remove(filename)
            else:
                await query.message.reply_text("⚠️ Data tidak ditemukan. Silakan kirim ulang chart.")
        except Exception as e:
            logger.exception("Error generating PDF")
            await query.message.reply_text(f"⚠️ Gagal membuat PDF: {e}")


async def journal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    pair_filter = None
    
    if context.args:
        if context.args[0] == "clear":
            from data.database import clear_user_journal
            clear_user_journal(user_id)
            await update.message.reply_text("🗑️ Journal berhasil dihapus.", parse_mode="Markdown")
            return
        pair_filter = context.args[0]
    
    from data.database import get_user_journal
    results = get_user_journal(user_id, limit=10, pair_filter=pair_filter)
    await update.message.reply_text(format_journal_list(results), parse_mode="Markdown")


async def weekly_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    report = format_weekly_report(user_id)
    
    schedule_msg = """
━━━━━━━━━━━━━━━━━━━━
⏰ *Jadwal Weekly Report*
📅 Setiap Senin, Jam 08:00 WITA

Gunakan `/report` untuk melihat kapan saja."""
    
    await update.message.reply_text(report + schedule_msg, parse_mode="Markdown")


async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action(action="typing")
    
    pair = context.args[0].upper() if context.args else None
    
    status_msg = await update.message.reply_text("📰 *Mengambil berita...*", parse_mode="Markdown")
    
    news_list = fetch_crypto_news(limit=15)
    response = format_news_response(news_list, pair)
    
    await status_msg.edit_text(response, parse_mode="Markdown")


async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action(action="typing")
    
    pair = context.args[0].upper() if context.args else "BTC"
    user_id = update.message.from_user.id
    
    last_text = last_analysis_text_cache.get(user_id, "")
    chart_context = last_text if last_text else None
    
    status_msg = await update.message.reply_text("🎯 *Menghitung prediksi...*", parse_mode="Markdown")
    
    try:
        prediction = get_market_prediction(chart_context, pair)
        response = format_market_prediction(prediction, pair)
        
        await status_msg.edit_text(response, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Predict error: {e}")
        await status_msg.edit_text(
            f"⚠️ Gagal mengambil prediksi untuk {pair}.\nCoba lagi nanti.",
            parse_mode="Markdown"
        )


async def prices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action(action="typing")
    
    status_msg = await update.message.reply_text("💰 *Mengambil harga...*", parse_mode="Markdown")
    
    prices = get_crypto_prices()
    
    if prices:
        await status_msg.edit_text(prices, parse_mode="Markdown")
    else:
        await status_msg.edit_text("⚠️ Gagal mengambil harga. Coba lagi nanti.", parse_mode="Markdown")


async def twitter_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = check_twitter_cookie()
    await update.message.reply_text(
        f"🐦 *Twitter Cookie Status*\n\n{status['message']}",
        parse_mode="Markdown"
    )


async def moon_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pair = context.args[0].upper() if context.args else None
    
    moon = get_moon_phase()
    
    if pair:
        from services.news_service import get_crypto_prices
        prices = get_crypto_prices()
        price_info = ""
        
        known_pairs = {"BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana", "XRP": "Ripple", 
                     "ADA": "Cardano", "BNB": "BNB", "DOGE": "Dogecoin", "AVAX": "Avalanche",
                     "DOT": "Polkadot", "MATIC": "Polygon", "LINK": "Chainlink", "UNI": "Uniswap"}
        
        coin_name = known_pairs.get(pair, pair)
        
        if pair in ["BTC", "ETH", "SOL"]:
            try:
                from services.news_fetcher import fetch_coingecko_news
                news = fetch_coingecko_news(5)
                for n in news:
                    if pair in n.get("title", "").upper():
                        chg = n.get("change_24h", 0)
                        price_info = f"\n📊 {pair} 24h: {chg:+.2f}%" if chg else ""
                        break
            except:
                pass
        
        phase_advice = ""
        if moon["phase"] == "New Moon":
            phase_advice = "🌓 Mulai siklus baru - Favor untuk entry baru"
        elif moon["phase"] == "Full Moon":
            phase_advice = "🌕 Peak volatility - Pertimbangkan take profit"
        elif moon["phase"] in ["Waxing Crescent", "First Quarter"]:
            phase_advice = "🌓 Building phase - Akumulasi posisi"
        elif moon["phase"] in ["Waning Gibbous", "Last Quarter"]:
            phase_advice = "🌗 Koreksi - Evaluasi posisi"
        else:
            phase_advice = "🌘 Penyiapan - Tunggu timing baru"
        
        await update.message.reply_text(
            f"🌙 *Moon Phase - {coin_name}*\n\n"
            f"Fase: *{moon['phase']}*\n"
            f"Iluminasi: {moon['illumination']}%\n"
            f"{price_info}\n\n"
            f"📋 *Insight:* {phase_advice}\n\n"
            f"_Bukan financial advice._",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"🌙 *Moon Phase*\n\n"
            f"Fase: *{moon['phase']}*\n"
            f"Iluminasi: {moon['illumination']}%\n"
            f"Timing: {moon['timing']}\n\n"
            f"Gunakan `/moon BTC` untuk insight token spesifik.\n\n"
            f"_Bukan financial advice._",
            parse_mode="Markdown"
        )


async def set_twitter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ *Format salah!*\n\n"
            "Gunakan: `/settwitter <auth_token> <ct0>`\n\n"
            "Cara mendapatkan:\n"
            "1. Login Twitter di browser\n"
            "2. DevTools (F12) → Application → Cookies → twitter.com\n"
            "3. Copy nilai 'auth_token' dan 'ct0'\n\n"
            "Contoh: `/settwitter abc123 xyz789`",
            parse_mode="Markdown"
        )
        return
    
    auth_token = context.args[0]
    ct0 = context.args[1]
    
    from data.cookie_manager import save_twitter_cookie
    success = save_twitter_cookie(auth_token, ct0)
    
    if success:
        await update.message.reply_text(
            "✅ *Twitter Cookie Berhasil Disimpan!*\n\n"
            "Cookie akan aktif selama 7 hari. "
            "Bot akan menggunakan Twitter untuk sentiment analysis.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "❌ Gagal menyimpan cookie. Coba lagi.",
            parse_mode="Markdown"
        )


async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    pair = context.args[0].upper() if context.args else None
    
    if not pair:
        await update.message.reply_text(
            "⚠️ *Format salah!*\n\nGunakan: /compare BTC\n\nAtau kirim 2 chart berurutan dengan pair sama.",
            parse_mode="Markdown"
        )
        return
    
    multi_key = f"{user_id}_{pair}"
    
    if multi_key not in multi_tf_cache or not multi_tf_cache[multi_key]:
        await update.message.reply_text(
            f"⚠️ *Belum ada chart untuk {pair}*\n\nKirim chart {pair} pertama dulu, lalu kirim chart timeframe lain.",
            parse_mode="Markdown"
        )
        return
    
    img1, tf1, cap1 = multi_tf_cache[multi_key]
    
    await update.message.reply_text(
        f"📊 Chart {pair} tersimpan:\n• Timeframe 1: {tf1}\n\nKirim chart {pair} dengan timeframe lain untuk comparison.",
        parse_mode="Markdown"
    )