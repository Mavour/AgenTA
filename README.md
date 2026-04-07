# Crypto TA Bot - AI Technical Analysis Telegram Bot

Bot Telegram untuk analisis teknikal kripto menggunakan AI (Qwen 3.6 Plus via OpenRouter).

## Fitur

- **Analisis Chart Otomatis** — Kirim foto chart, dapatkan analisis teknikal lengkap
- **Tanya Jawab** — Kirim teks biasa untuk bertanya seputar kripto & trading
- **Kalkulator Risk:Reward** — Hitung R:R ratio dengan command `/rr`
- **Auto-Detect Mode** — Otomatis deteksi apakah user kirim foto atau teks
- **Typing Indicator** — Bot show "typing..." saat memproses
- **Retry Button** — Tombol untuk analisis ulang
- **Anti-Hallucination** — Bot tidak mengarang jawaban untuk Q&A

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup environment:**
   ```bash
   copy .env.example .env
   ```
   Isi `.env` dengan:
   - `TELEGRAM_TOKEN` — Token dari @BotFather
   - `OPENROUTER_API_KEY` — API key dari https://openrouter.ai

3. **Jalankan bot:**
   ```bash
   python bot.py
   ```

## Command List

| Command | Fungsi |
|---------|--------|
| `/start` | Welcome message + panduan |
| `/help` | Panduan lengkap |
| `/rr <entry> <sl> <tp>` | Hitung Risk:Reward ratio |
| **Kirim foto** | Analisis teknikal chart |
| **Kirim teks** | Tanya jawab seputar kripto & trading |

## Struktur File

```
├── .env.example            # Template env vars
├── requirements.txt        # Dependencies
├── config.py               # Load & validate env
├── prompts.py              # System prompts (chart analysis + Q&A)
├── openrouter_client.py    # OpenRouter API client
├── utils.py                # R:R calculator, formatting helpers
├── handlers.py             # All Telegram handlers
└── bot.py                  # Main entry point
```

## Model

- **Provider:** OpenRouter
- **Model:** `qwen/qwen3.6-plus:free`
- **Temperature:** 0.3 (konservatif untuk analisis yang lebih objektif)
- **Max Tokens:** 2048

## Disclaimer

Bot ini bersifat edukatif dan bukan merupakan saran finansial. Selalu lakukan riset mandiri (DYOR).
