import base64
import asyncio
import logging
import httpx
from config import OPENROUTER_API_KEY

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_CHAT = "minimax/minimax-m2.5:free"
MODEL_VISION = "nvidia/nemotron-nano-12b-v2-vl:free"
TIMEOUT = 120
MAX_RETRIES = 3
BASE_RETRY_DELAY = 3


class OpenRouterError(Exception):
    pass


class RateLimitError(OpenRouterError):
    pass


def _encode_image(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


async def _make_request(system_prompt: str, user_content: list, retry_count: int = 0, model: str = MODEL_CHAT) -> str:
    logger.info(f"Requesting model: {model}, retry: {retry_count}")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/cryptota-bot",
        "X-Title": "Crypto TA Bot",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.3,
        "max_tokens": 2048,
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(OPENROUTER_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            if "choices" not in data or len(data["choices"]) == 0:
                raise OpenRouterError("Respons API tidak valid, tidak ada choices")

            return data["choices"][0]["message"]["content"]

        except httpx.TimeoutException:
            raise OpenRouterError("Request timeout — coba lagi dalam beberapa detik")

        except httpx.HTTPStatusError as e:
            error_body = e.response.text[:500]
            logger.error(f"HTTP {e.response.status_code}: {error_body}")
            if e.response.status_code == 429:
                if retry_count < MAX_RETRIES:
                    delay = BASE_RETRY_DELAY * (2 ** retry_count)
                    logger.info(f"Rate limited, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    return await _make_request(system_prompt, user_content, retry_count + 1, model)
                raise RateLimitError("Rate limit tercapai. Silakan tunggu 30 detik lalu coba lagi.")
            elif e.response.status_code >= 500:
                if retry_count < MAX_RETRIES:
                    delay = BASE_RETRY_DELAY * (2 ** retry_count)
                    logger.info(f"Server error, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    return await _make_request(system_prompt, user_content, retry_count + 1, model)
                raise OpenRouterError("Server OpenRouter sedang gangguan, coba lagi nanti")
            raise OpenRouterError(f"Error dari OpenRouter: {e.response.status_code}")

        except httpx.ConnectError:
            raise OpenRouterError("Gagal terhubung ke OpenRouter, periksa koneksi internet")

        except KeyError:
            raise OpenRouterError("Format respons API tidak dikenali")


async def analyze_chart(image_bytes: bytes, caption: str = "", pair: str = "BTC") -> str:
    from utils import get_moon_phase
    
    moon = get_moon_phase()
    
    base64_image = _encode_image(image_bytes)
    user_content = [
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
        }
    ]

    if caption.strip():
        user_content.append({
            "type": "text",
            "text": f"Konteks tambahan dari user: {caption.strip()}"
        })
    else:
        user_content.append({
            "type": "text",
            "text": "Silakan analisis chart ini."
        })

    moon_advice = "Favor untuk entry baru" if moon["phase"] == "New Moon" else "Volatility tinggi - take profit" if moon["phase"] == "Full Moon" else "Building phase" if moon["phase"] in ["Waxing Crescent", "First Quarter"] else "Evaluasi posisi"
    
    prompt = CHART_ANALYSIS_PROMPT.replace("{moon_phase}", moon["phase"]).replace("{moon_illumination}", str(moon["illumination"])).replace("{pair}", pair).replace("{MOON_INSIGHT}", moon_advice)
    return await _make_request(prompt, user_content, model=MODEL_VISION)


async def answer_question(text: str, context: dict = None) -> str:
    from prompts import QA_PROMPT, FALLBACK_PROMPT
    
    if "blur" in text.lower() or "tidak jelas" in text.lower():
        return await _make_request(FALLBACK_PROMPT, [{"type": "text", "text": text}], model=MODEL_CHAT)
    
    price_ctx = "Tidak ada" if context is None else context.get("price", "Tidak ada")
    news_ctx = "Tidak ada" if context is None else context.get("news", "Tidak ada")
    chart_ctx = "Tidak ada" if context is None else context.get("chart", "Tidak ada")
    
    prompt = QA_PROMPT.format(
        price_context=price_ctx,
        news_context=news_ctx,
        chart_context=chart_ctx,
        question=text
    )
    
    return await _make_request(prompt, [{"type": "text", "text": text}], model=MODEL_CHAT)
