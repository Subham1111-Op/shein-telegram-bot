import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

# ================= ENV =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("BOT_TOKEN or CHAT_ID missing")

CHAT_ID = int(CHAT_ID)

# ================= CONFIG =================

CHECK_INTERVAL = 10

MEN_API = "https://www.sheinindia.in/api/category/sverse-5939-37961"

session = requests.Session()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": "https://www.sheinindia.in/",
    "Origin": "https://www.sheinindia.in",
}

PARAMS = {
    "fields": "SITE",
    "currentPage": 0,
    "pageSize": 40,
    "format": "json",
    "query": ":relevance",
}

# ================= STATE =================

alerts_enabled = True
seen_stock = {}

# ================= LOG =================

logging.basicConfig(level=logging.INFO)

# ================= KEYBOARD =================

def keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Alerts ON", callback_data="on"),
         InlineKeyboardButton("🔴 Alerts OFF", callback_data="off")],
        [InlineKeyboardButton("📊 Bot Status", callback_data="status")]
    ])

# ================= FETCH =================

def fetch_products():
    try:
        r = session.get(
            MEN_API,
            headers=HEADERS,
            params=PARAMS,
            timeout=20
        )
        r.raise_for_status()
        return r.json().get("info", {}).get("products", [])
    except Exception as e:
        logging.error(f"Shein fetch failed: {e}")
        return []

# ================= STOCK JOB =================

def stock_job(app: Application):
    global seen_stock

    if not alerts_enabled:
        return

    products = fetch_products()

    for p in products:
        item_id = p.get("goods_id")
        name = p.get("goods_name")
        url = p.get("goods_url")
        skus = p.get("skus", [])

        if not item_id or not skus:
            continue

        if item_id not in seen_stock:
            seen_stock[item_id] = set()

        for sku in skus:
            sku_id = sku.get("sku_id")
            stock = sku.get("stock", 0)

            if stock > 0 and sku_id not in seen_stock[item_id]:
                seen_stock[item_id].add(sku_id)

                link = f"https://www.sheinindia.in{url}"

                app.bot.send_message(
                    chat_id=CHAT_ID,
                    text=f"🔥 STOCK AVAILABLE\n\n{name}\n\n{link}",
                    disable_web_page_preview=False,
                )

# ================= HANDLERS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Shein Verse MEN Stock Bot\n\nReady 🚀",
        reply_markup=keyboard()
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global alerts_enabled
    q = update.callback_query
    await q.answer()

    if q.data == "on":
        alerts_enabled = True
        await q.edit_message_text("🟢 Alerts ON", reply_markup=keyboard())

    elif q.data == "off":
        alerts_enabled = False
        await q.edit_message_text("🔴 Alerts OFF", reply_markup=keyboard())

    elif q.data == "status":
        await q.edit_message_text(
            f"📊 Status\nAlerts: {'ON' if alerts_enabled else 'OFF'}\nBot: Alive ✅",
            reply_markup=keyboard()
        )

# ================= MAIN =================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))

    scheduler = BackgroundScheduler()
    scheduler.add_job(stock_job, "interval", seconds=CHECK_INTERVAL, args=[app])
    scheduler.start()

    logging.info("Bot running safely (403 fixed)")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
