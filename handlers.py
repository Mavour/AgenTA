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
        "⏳ *Sedang menganalisis chart...*\n\nMohon tunggu sebentar.",
        parse_mode="Markdown"
    )

    photo = update.message.photo[-1]
    caption = update.message.caption or ""
    user_id = update.message.from_user.id

    try:
        file = await photo.get_file()
        image_bytes = await file.download_as_bytearray()
        image_bytes = bytes(image_bytes)

        photo_cache[user_id] = (image_bytes, caption)
        last_analysis_cache[user_id] = "chart"

        analysis = await analyze_chart(image_bytes, caption)
        last_analysis_text_cache[user_id] = analysis

        pair = caption.split()[0] if caption else "Unknown"
        signal = "bullish" if "bullish" in analysis.lower() else "bearish" if "bearish" in analysis.lower() else None
        save_analysis(user_id, analysis, pair=pair, timeframe="Unknown", signal=signal)

        keyboard = [
            [InlineKeyboardButton("🔄 Analisis Ulang", callback_data="retry_analysis"), InlineKeyboardButton("📄 PDF", callback_data="export_pdf")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await status_msg.edit_text(analysis, parse_mode="Markdown", reply_markup=reply_markup)

    except Exception as e:
        logger.exception("Error in photo handler: %s", type(e).__name__)
        try:
            await status_msg.edit_text(
                format_error_message("Terjadi kesalahan saat memproses gambar."),
                parse_mode="Markdown"
            )
        except Exception:
            pass


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.caption:
        return

    text = update.message.text.strip()

    if text.startswith("/"):
        return

    if text == "📊 Analisis Chart":
        await update.message.reply_text(
            "📸 Kirim foto chart Anda dan saya akan menganalisisnya secara teknikal.\n\n💡 *Tips:* Tambahkan caption untuk konteks (contoh: \"BTC/USDT 4H\")",
            parse_mode="Markdown",
        )
        return

    if text == "💬 Tanya Jawab":
        await update.message.reply_text(
            "💬 Silakan ketik pertanyaan Anda seputar:\n\n• Konsep teknikal analysis\n• Penjelasan indikator\n• Strategi trading\n• Istilah kripto & trading",
            parse_mode="Markdown",
        )
        return

    if text == "📖 Panduan":
        await help_command(update, context)
        return

    if text == "📔 Journal":
        from data.database import get_user_journal
        results = get_user_journal(update.message.from_user.id, limit=10)
        await update.message.reply_text(format_journal_list(results), parse_mode="Markdown")
        return

    if text == "📰 News":
        status_msg = await update.message.reply_text("📰 *Mengambil berita...*", parse_mode="Markdown")
        news_list = fetch_crypto_news(limit=10)
        await status_msg.edit_text(format_news_response(news_list), parse_mode="Markdown")
        return

    if text == "💰 Harga":
        status_msg = await update.message.reply_text("💰 *Mengambil harga...*", parse_mode="Markdown")
        prices = get_crypto_prices()
        if prices:
            await status_msg.edit_text(prices, parse_mode="Markdown")
        else:
            await status_msg.edit_text("⚠️ Gagal mengambil harga.", parse_mode="Markdown")
        return

    if text == "📊 Report":
        await update.message.reply_text(format_weekly_report(update.message.from_user.id), parse_mode="Markdown")
        return

    text_lower = text.lower()
    is_trend_question = any(pattern in text_lower for pattern in TREND_TRIGGER_PATTERNS)

    if is_trend_question:
        await update.message.chat.send_action(action="typing")
        
        user_id = update.message.from_user.id
        last_text = last_analysis_text_cache.get(user_id, "")
        
        status_msg = await update.message.reply_text(
            "🔮 *Menghitung market prediction...*\n\nMenggabungkan analisis chart + news + social media",
            parse_mode="Markdown"
        )
        
        try:
            chart_context = last_text if last_text else None
            pair = "BTC"
            if user_id in photo_cache:
                _, caption = photo_cache[user_id]
                pair = caption.split()[0] if caption else "BTC"
            
            prediction = get_market_prediction(chart_context, pair)
            prediction_text = format_market_prediction(prediction)
            
            last_analysis_cache[user_id] = "trend"
            await status_msg.edit_text(prediction_text, parse_mode="Markdown")
            return

        except Exception as e:
            logger.error(f"Error in market prediction: {type(e).__name__}: {e}")
            await status_msg.edit_text(
                "⚠️ Gagal menghitung prediksi market. Coba lagi nanti.",
                parse_mode="Markdown"
            )
            return

    await update.message.chat.send_action(action="typing")

    user_id = update.message.from_user.id
    
    context_hint = ""
    last_analysis = last_analysis_cache.get(user_id, "")
    last_text = last_analysis_text_cache.get(user_id, "")
    
    if last_analysis == "chart" and last_text:
        truncated_text = last_text[:500] if len(last_text) > 500 else last_text
        context_hint = f"""Konteks: User baru saja mengirim foto chart dan mendapat analisis teknikal berikut:

{truncated_text}

Berdasarkan analisis di atas, jawab pertanyaan berikut: """
    
    status_msg = await update.message.reply_text(
        "⏳ *Sedang memproses pertanyaan...*\n\nMohon tunggu sebentar.",
        parse_mode="Markdown"
    )

    try:
        logger.info(f"Processing text question for user {user_id}")
        full_text = context_hint + text
        logger.info(f"Full text length: {len(full_text)}")
        response = await answer_question(full_text)
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
                image_bytes, caption = photo_cache[user_id]

            if image_bytes:
                analysis = await analyze_chart(image_bytes, caption)

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
                    _, caption = photo_cache[user_id]
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