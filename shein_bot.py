import aiohttp
import random
import json
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ========== CONFIG ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")   # Railway Variables
CHAT_ID = 7855120289   # 👈 APNA REAL CHAT ID

CHECK_INTERVAL = 12   # seconds
PAGES_TO_SCAN = 2

ALERTS_ON = False
BOT_ALIVE = True

SEEN_FILE = "seen_products.json"
SEEN_PRODUCTS = set()

BASE_API = "https://www.sheinindia.in/api/category/sverse-5939-37961?fields=SITE&pageSize=40&format=json&query=%3Arelevance%3Agenderfilter%3AMen&facets=genderfilter%3AMen&platform=Desktop&currentPage={page}"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Linux; Android 13)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
]

# ============================

def load_seen():
    global SEEN_PRODUCTS
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f:
                SEEN_PRODUCTS = set(json.load(f))
        except:
            SEEN_PRODUCTS = set()

def save_seen():
    try:
        with open(SEEN_FILE, "w") as f:
            json.dump(list(SEEN_PRODUCTS), f)
    except:
        pass

def build_product_link(p):
    goods_id = p.get("goods_id")
    goods_sn = p.get("goods_sn", "")
    return f"https://www.sheinindia.in/{goods_sn}-p-{goods_id}.html"

async def fetch_page(session, page):
    url = BASE_API.format(page=page)
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json",
        "Referer": "https://www.sheinindia.in/"
    }
    try:
        async with session.get(url, headers=headers, timeout=10) as resp:
            return await resp.json()
    except:
        return {}

# ===== JOB QUEUE STOCK CHECKER (SAFE) =====

async def stock_job(context: ContextTypes.DEFAULT_TYPE):
    global ALERTS_ON

    if not ALERTS_ON:
        return

    if not hasattr(context.application, "http_session"):
        context.application.http_session = aiohttp.ClientSession()

    session = context.application.http_session

    for page in range(PAGES_TO_SCAN):
        data = await fetch_page(session, page)
        products = data.get("info", {}).get("products", [])

        for p in products:
            try:
                pid = str(p.get("goods_id"))
                name = p.get("goods_name")
                stock = p.get("stock", 0)
                price = p.get("salePrice", {}).get("amount", "")

                if stock and stock > 0 and pid not in SEEN_PRODUCTS:
                    SEEN_PRODUCTS.add(pid)
                    save_seen()

                    link = build_product_link(p)

                    msg = (
                        f"🔥 IN STOCK ALERT!\n\n"
                        f"🛍 {name}\n"
                        f"💰 Price: {price}\n"
                        f"📦 Stock: {stock}\n\n"
                        f"🔗 Buy Now:\n{link}"
                    )

                    await context.application.bot.send_message(
                        chat_id=CHAT_ID,
                        text=msg
                    )
            except:
                continue

# ===== Telegram Handlers =====

async def start(update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🟢 Stock Alerts ON", callback_data="on")],
        [InlineKeyboardButton("🔴 Stock Alerts OFF", callback_data="off")],
        [InlineKeyboardButton("📡 Bot Status", callback_data="status")]
    ]

    await update.message.reply_text(
        "🤖 Shein Verse PRO Bot Ready!\n\nChoose option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update, context: ContextTypes.DEFAULT_TYPE):
    global ALERTS_ON

    query = update.callback_query
    await query.answer()

    if query.data == "on":
        ALERTS_ON = True
        await query.edit_message_text("🟢 Stock Alerts TURNED ON!")

    elif query.data == "off":
        ALERTS_ON = False
        await query.edit_message_text("🔴 Stock Alerts TURNED OFF!")

    elif query.data == "status":
        status = "🟢 ALIVE & RUNNING" if BOT_ALIVE else "🔴 DOWN"
        alerts = "ON" if ALERTS_ON else "OFF"

        await query.edit_message_text(
            f"🤖 Bot Status:\n\nStatus: {status}\nStock Alerts: {alerts}\nSeen Items: {len(SEEN_PRODUCTS)}"
        )

# ===== Main (RAILWAY + PTB OFFICIAL SAFE WAY) =====

def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN not set in environment variables!")
        return

    load_seen()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    # ✅ SAFE BACKGROUND LOOP (NO ASYNCIO CRASH)
    app.job_queue.run_repeating(stock_job, interval=CHECK_INTERVAL, first=10)

    print("🚀 Shein Verse PRO Bot started (JOB QUEUE MODE)...")
    app.run_polling()

if __name__ == "__main__":
    main()
