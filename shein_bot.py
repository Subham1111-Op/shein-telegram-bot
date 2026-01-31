import os
import asyncio
import logging
import requests
from datetime import datetime

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# ================= ENV =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("Missing BOT_TOKEN or CHAT_ID")

# ================= CONFIG =================

API_URL = "https://www.sheinindia.in/api/category/sverse-5939-37961"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13)",
    "Accept": "application/json",
    "Referer": "https://www.sheinindia.in/",
}

PARAMS = {
    "fields": "SITE",
    "currentPage": 0,
    "pageSize": 40,
    "format": "json",
    "query": ":relevance",
}

CHECK_INTERVAL = 8  # FAST
seen_items = set()
session = requests.Session()

logging.basicConfig(level=logging.INFO)

BOT_START_TIME = datetime.utcnow()

# ================= COMMANDS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Shein Verse MEN Stock Bot*\n\n"
        "✅ Status: Running\n"
        "⚡ Speed: Fast\n"
        "🧠 Mode: Pro\n\n"
        "Commands:\n"
        "/status – bot status\n"
        "/ping – test reply",
        parse_mode="Markdown"
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Pong! Bot alive.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = datetime.utcnow() - BOT_START_TIME
    await update.message.reply_text(
        f"📊 *Bot Status*\n\n"
        f"🟢 Running\n"
        f"⏱ Uptime: {str(uptime).split('.')[0]}\n"
        f"📦 Tracked items: {len(seen_items)}",
        parse_mode="Markdown"
    )

# ================= STOCK CHECK =================

async def stock_checker(app):
    await asyncio.sleep(5)

    while True:
        try:
            r = session.get(
                API_URL,
                headers=HEADERS,
                params=PARAMS,
                timeout=20
            )

            if r.status_code != 200:
                logging.warning(f"HTTP {r.status_code}")
                await asyncio.sleep(5)
                continue

            data = r.json()
            products = data.get("info", {}).get("products", [])

            for p in products:
                name = p.get("goods_name")
                url = p.get("goods_url")
                skus = p.get("skus", [])
                pid = p.get("goods_id")

                if not pid or not skus:
                    continue

                for sku in skus:
                    stock = sku.get("stock", 0)
                    sku_id = sku.get("sku_id")

                    key = f"{pid}-{sku_id}"

                    if stock > 0 and key not in seen_items:
                        seen_items.add(key)
                        link = f"https://www.sheinindia.in{url}"

                        await app.bot.send_message(
                            chat_id=CHAT_ID,
                            text=(
                                "🔥 *STOCK AVAILABLE*\n\n"
                                f"{name}\n\n"
                                f"{link}"
                            ),
                            parse_mode="Markdown"
                        )

        except Exception as e:
            logging.error(f"Stock error: {e}")

        await asyncio.sleep(CHECK_INTERVAL)

# ================= MAIN =================

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("status", status))

    # IMPORTANT FIX
    await app.bot.delete_webhook(drop_pending_updates=True)

    app.create_task(stock_checker(app))

    logging.info("🤖 Pro bot started (Railway stable)")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
