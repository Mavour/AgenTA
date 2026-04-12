import logging
import re
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Tuple, Optional, List

logger = logging.getLogger(__name__)

WIDTH = 800
HEIGHT = 600
BG_COLOR = (15, 15, 20)
TEXT_COLOR = (220, 220, 220)
GREEN = (0, 255, 127)
RED = (255, 99, 71)
BLUE = (100, 149, 237)
YELLOW = (255, 215, 0)
ORANGE = (255, 165, 0)
PURPLE = (138, 43, 226)

SMC_ZONE_COLOR = (138, 43, 226, 50)
LINE_COLOR = (70, 70, 80)


def parse_analysis(analysis_text: str) -> Dict:
    """Parse analysis text to extract trading data"""
    data = {
        "pair": "BTC/USDT",
        "trend": "SIDEWAYS",
        "strength": 5,
        "supports": [],
        "resistances": [],
        "entry": None,
        "stop_loss": None,
        "take_profit": [],
        "rr": 2.0,
        "invalid_level": None,
        "ob_zones": [],
        "fvg_zones": [],
        "liquidity_grab": None,
    }
    
    if not analysis_text:
        return data
    
    text = analysis_text.upper()
    
    pair_match = re.search(r"([A-Z]{2,10})/\s*US[D]?T", text)
    if pair_match:
        data["pair"] = pair_match.group(1).replace("/", "/") + "/USDT"
    
    trend_match = re.search(r"T[R][E][N]:\s*(BULLISH|BEARISH|SIDEWAYS)", text, re.IGNORECASE)
    if trend_match:
        data["trend"] = trend_match.group(1).title()
    
    strength_match = re.search(r"KEKUATAN:\s*(\d+)", text)
    if strength_match:
        data["strength"] = int(strength_match.group(1))
    
    support_matches = re.findall(r"SUPPORT[:\s]*[\$\u0024]?(\d+[,.]?\d*)", text, re.IGNORECASE)
    data["supports"] = [float(s.replace(",", "")) for s in support_matches[:2]]
    
    resistance_matches = re.findall(r"RESISTANCE[:\s]*[\$\u0024]?(\d+[,.]?\d*)", text, re.IGNORECASE)
    data["resistances"] = [float(r.replace(",", "")) for r in resistance_matches[:2]]
    
    entry_match = re.search(r"ENTRY[:\s]*[\$\u0024]?(\d+[,.]?\d*)", text, re.IGNORECASE)
    if entry_match:
        data["entry"] = float(entry_match.group(1).replace(",", ""))
    
    sl_match = re.search(r"STOP\s*LOSS[:\s]*[\$\u0024]?(\d+[,.]?\d*)", text, re.IGNORECASE)
    if sl_match:
        data["stop_loss"] = float(sl_match.group(1).replace(",", ""))
    
    tp_matches = re.findall(r"TAKE\s*PROFIT[:\s]*[\$\u0024]?(\d+[,.]?\d*)", text, re.IGNORECASE)
    data["take_profit"] = [float(tp.replace(",", "")) for tp in tp_matches[:2]]
    
    rr_match = re.search(r"RISK[:]?\s*REWARD[:\s]*1[:\s]*(\d+)", text, re.IGNORECASE)
    if rr_match:
        data["rr"] = float(rr_match.group(1))
    
    inv_match = re.search(r"(?:INVALIDASI|INVALID)[:\s]*[\$\u0024]?(\d+[,.]?\d*)", text, re.IGNORECASE)
    if inv_match:
        data["invalid_level"] = float(inv_match.group(1).replace(",", ""))
    
    ob_matches = re.findall(r"ORDER\s*BLOCK.*?[\$\u0024]?(\d+[,.]?\d+)", text, re.IGNORECASE)
    data["ob_zones"] = [float(o.replace(",", "")) for o in ob_matches[:2]]
    
    fvg_matches = re.findall(r"FAIR\s*VALUE\s*GAP.*?[\$\u0024]?(\d+[,.]?\d+)", text, re.IGNORECASE)
    data["fvg_zones"] = [float(f.replace(",", "")) for f in fvg_matches[:2]]
    
    liq_match = re.search(r"LIQUIDATION.*?[\$\u0024]?(\d+[,.]?\d+)", text, re.IGNORECASE)
    if liq_match:
        data["liquidity_grab"] = float(liq_match.group(1).replace(",", ""))
    
    return data


def draw_rounded_rectangle(draw, xy, radius=10, fill=None, outline=None):
    """Draw rounded rectangle"""
    x1, y1, x2, y2 = xy
    draw.rectangle([x1+radius, y1, x2-radius, y2], fill=fill, outline=outline)
    draw.rectangle([x1, y1+radius, x2, y2-radius], fill=fill, outline=outline)
    draw.pieslice([x1, y1, x1+2*radius, y1+2*radius], 180, 270, fill=fill, outline=outline)
    draw.pieslice([x2-2*radius, y1, x2, y1+2*radius], 270, 360, fill=fill, outline=outline)
    draw.pieslice([x1, y2-2*radius, x1+2*radius, y2], 90, 180, fill=fill, outline=outline)
    draw.pieslice([x2-2*radius, y2-2*radius, x2, y2], 0, 90, fill=fill, outline=outline)


def generate_chart_image(analysis_text: str, pair: str = "BTC") -> Image.Image:
    """Generate annotated chart image from analysis"""
    data = parse_analysis(analysis_text)
    data["pair"] = pair.upper() + "/USDT"
    
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    header_h = 60
    draw.rectangle([0, 0, WIDTH, header_h], fill=(25, 25, 35))
    
    trend_emoji = "📈" if data["trend"].upper() == "BULLISH" else "📉" if data["trend"].upper() == "BEARISH" else "➡️"
    trend_color = GREEN if data["trend"].upper() == "BULLISH" else RED if data["trend"].upper() == "BEARISH" else BLUE
    
    draw.text((20, 18), f"{data['pair']} {trend_emoji} {data['trend'].upper()}", fill=trend_color, font=font_large)
    draw.text((550, 18), f"Strength: {data['strength']}/10", fill=TEXT_COLOR, font=font_small)
    
    draw.line([0, header_h, WIDTH, header_h], fill=LINE_COLOR, width=2)
    
    sections = [
        ("SUPPORTS", data["supports"], GREEN),
        ("RESISTANCES", data["resistances"], RED),
    ]
    
    y_offset = 80
    
    for label, levels, color in sections:
        if levels:
            draw.text((20, y_offset), f"● {label}:", fill=TEXT_COLOR, font=font_medium)
            y_offset += 30
            for lvl in levels:
                draw.text((40, y_offset), f"  ${lvl:,.0f}", fill=color, font=font_small)
                y_offset += 22
            y_offset += 15
    
    if data["entry"]:
        y_offset += 10
        draw.text((20, y_offset), "🎯 ENTRY:", fill=TEXT_COLOR, font=font_medium)
        draw.text((140, y_offset), f"${data['entry']:,.0f}", fill=GREEN, font=font_small)
        y_offset += 28
    
    if data["stop_loss"]:
        draw.text((20, y_offset), "🛡️ STOP LOSS:", fill=TEXT_COLOR, font=font_medium)
        draw.text((150, y_offset), f"${data['stop_loss']:,.0f}", fill=RED, font=font_small)
        y_offset += 28
    
    if data["take_profit"]:
        draw.text((20, y_offset), "🎯 TAKE PROFIT:", fill=TEXT_COLOR, font=font_medium)
        for tp in data["take_profit"]:
            draw.text((160, y_offset), f"${tp:,.0f}", fill=GREEN, font=font_small)
            y_offset += 22
        y_offset += 10
    
    if data["rr"]:
        draw.text((20, y_offset), f"📊 R:R = 1:{data['rr']}", fill=YELLOW, font=font_medium)
        y_offset += 35
    
    smc_y = y_offset + 10
    draw.text((20, smc_y), "📊 SMART MONEY:", fill=PURPLE, font=font_medium)
    smc_y += 28
    
    if data["ob_zones"]:
        draw.text((30, smc_y), f"Order Block: ${data['ob_zones'][0]:,.0f}", fill=PURPLE, font=font_small)
        smc_y += 22
    
    if data["fvg_zones"]:
        draw.text((30, smc_y), f"FVG: ${data['fvg_zones'][0]:,.0f}", fill=ORANGE, font=font_small)
        smc_y += 22
    
    if data["liquidity_grab"]:
        draw.text((30, smc_y), f"Liquidation: ${data['liquidity_grab']:,.0f}", fill=RED, font=font_small)
        smc_y += 22
    
    if data["invalid_level"]:
        draw.text((20, smc_y + 25), f"⚠️ Invalid if > ${data['invalid_level']:,.0f}", fill=YELLOW, font=font_small)
    
    footer_y = HEIGHT - 45
    draw.line([0, footer_y, WIDTH, footer_y], fill=LINE_COLOR, width=2)
    draw.rectangle([0, footer_y, WIDTH, HEIGHT], fill=(25, 25, 35))
    draw.text((20, footer_y + 12), "Bukan financial advice. Selalu lakukan riset mandiri (DYOR).", fill=(120, 120, 120), font=font_small)
    draw.text((550, footer_y + 12), "AgenTA Technical Analysis", fill=(80, 80, 100), font=font_small)
    
    return img


def generate_analysis_image(analysis_text: str, pair: str = "BTC") -> Optional[bytes]:
    """Generate chart image and return as bytes"""
    try:
        img = generate_chart_image(analysis_text, pair)
        import io
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.getvalue()
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        return None