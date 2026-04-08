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

logger = logging.getLogger(__name__)

MENU_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📊 Analisis Chart"), KeyboardButton("💬 Tanya Jawab")],
        [KeyboardButton("📐 Hitung R:R"), KeyboardButton("📖 Panduan")],
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
)

photo_cache = {}
last_analysis_cache = {}


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


async def rr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) != 3:
        await update.message.reply_text(
            "⚠️ *Format salah!*\n\n"
            "Gunakan: `/rr <entry> <sl> <tp>`\n"
            "Contoh: `/rr 65000 63000 70000`",
            parse_mode="Markdown",
        )
        return

    try:
        entry = float(context.args[0])
        sl = float(context.args[1])
        tp = float(context.args[2])
    except ValueError:
        await update.message.reply_text(
            "⚠️ Angka tidak valid! Gunakan format:\n`/rr 65000 63000 70000`",
            parse_mode="Markdown",
        )
        return

    result = calculate_rr(entry, sl, tp)
    await update.message.reply_text(
        format_rr_result(result),
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

        keyboard = [
            [InlineKeyboardButton("🔄 Analisis Ulang", callback_data="retry_analysis")]
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

    if text == "📐 Hitung R:R":
        await update.message.reply_text(
            "📐 Masukkan entry, stop loss, dan take profit:\n\nFormat: `/rr <entry> <sl> <tp>`\nContoh: `/rr 65000 63000 70000`",
            parse_mode="Markdown",
        )
        return

    if text == "📖 Panduan":
        await help_command(update, context)
        return

    await update.message.chat.send_action(action="typing")

    user_id = update.message.from_user.id
    
    context_hint = ""
    if user_id in last_analysis_cache and last_analysis_cache[user_id] == "chart":
        context_hint = "User baru saja mengirim foto chart dan mendapat analisis. Pertanyaan ini kemungkinan berkaitan dengan chart tersebut. "

    status_msg = await update.message.reply_text(
        "⏳ *Sedang memproses pertanyaan...*\n\nMohon tunggu sebentar.",
        parse_mode="Markdown"
    )

    try:
        full_text = context_hint + text
        response = await answer_question(full_text)
        last_analysis_cache[user_id] = "text"
        await status_msg.edit_text(response, parse_mode="Markdown")

    except Exception as e:
        logger.exception("Error in text handler: %s", type(e).__name__)
        try:
            await status_msg.edit_text(
                format_error_message("Terjadi kesalahan saat memproses pertanyaan."),
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
                    [InlineKeyboardButton("🔄 Analisis Ulang", callback_data="retry_analysis")]
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