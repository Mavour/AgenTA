import os
import json
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

COOKIE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "twitter_cookie.json")


def check_twitter_cookie() -> dict:
    """Check current Twitter cookie status"""
    try:
        if not os.path.exists(COOKIE_FILE):
            return {
                "status": "not_set",
                "message": "Cookie Twitter belum diatur. Gunakan /settwitter untuk mengatur."
            }
        
        with open(COOKIE_FILE, 'r') as f:
            data = json.load(f)
        
        if "expires" in data:
            expires = datetime.fromisoformat(data["expires"])
            if expires < datetime.now():
                return {
                    "status": "expired",
                    "message": f"⚠️ Cookie Twitter expired! Silakan perbarui dengan command /settwitter"
                }
            
            remaining = (expires - datetime.now()).days
            return {
                "status": "active",
                "message": f"✅ Cookie aktif ({remaining} hari tersisa)",
                "expires": expires.strftime("%Y-%m-%d %H:%M")
            }
        
        return {"status": "unknown", "message": "Status cookie tidak jelas"}
    
    except Exception as e:
        logger.error(f"Error checking cookie: {e}")
        return {"status": "error", "message": str(e)}


def save_twitter_cookie(auth_token: str, ct0: str) -> bool:
    """Save Twitter cookie with 7 day expiration"""
    try:
        expires = datetime.now() + timedelta(days=7)
        
        cookie_data = {
            "auth_token": auth_token,
            "ct0": ct0,
            "expires": expires.isoformat(),
            "created_at": datetime.now().isoformat()
        }
        
        os.makedirs(os.path.dirname(COOKIE_FILE), exist_ok=True)
        with open(COOKIE_FILE, 'w') as f:
            json.dump(cookie_data, f)
        
        logger.info(f"Twitter cookie saved, expires: {expires}")
        return True
    
    except Exception as e:
        logger.error(f"Error saving cookie: {e}")
        return False


async def send_cookie_expiry_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send alert about expired cookie to user"""
    await update.message.reply_text(
        "⚠️ *Twitter Cookie Expired!*\n\n"
        "Cookie Twitter Anda sudah kedaluwarsa. Untuk melanjutkan scraping Twitter:\n\n"
        "1. Login ke Twitter di browser\n"
        "2. DevTools → Application → Cookies → twitter.com\n"
        "3. Copy nilai 'auth_token' dan 'ct0'\n"
        "4. Kirim ke bot dengan format:\n"
        "`/settwitter <auth_token> <ct0>`\n\n"
        "Atau gunakan command `/settwitter` untuk panduan lebih lengkap.",
        parse_mode="Markdown"
    )


def clear_twitter_cookie() -> bool:
    """Clear stored Twitter cookie"""
    try:
        if os.path.exists(COOKIE_FILE):
            os.remove(COOKIE_FILE)
            logger.info("Twitter cookie cleared")
            return True
    except Exception as e:
        logger.error(f"Error clearing cookie: {e}")
    return False


from datetime import timedelta