import os
import logging
import requests
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from apscheduler.schedulers.background import BackgroundScheduler

# ================= ENV =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("BOT_TOKEN or CHAT_ID missing")

CHAT_ID = int(CHAT_ID)

# ================= CONFIG =================

CHECK_INTERVAL = 10  # seconds (fast)

MEN_API = (
    "https://www.sheinindia.in/api/category/sverse-5939-37961"
    "?fields=SITE&currentPage=0&pageSize=40&format=json&query=:relevance"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}

# ================= STATE =================

alerts_enabled = True
seen_stock = {}  # item_id -> set(size_ids)

# ================= LOG =================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# ================= KEYBOARD =================

def main_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🟢 Stock Alerts ON", callback_data="on"),
                InlineKeyboardButton("🔴 Stock Alerts OFF", callback_data="off"),
            ],
            [
                InlineKeyboardButton("📊 Bot Status", callback_data="status"),
            ],
        ]
    )

# ================= API =================

def fetch_products():
    try:
        r = requests.get(MEN_API, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.json().get("info", {}).get("products", [])
    except Exception as e:
        logging.error(f"Fetch error: {e}")
        return []

# ================= STOCK CHECK =================

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
            size_id = sku.get("sku_id")
            stock = sku.get("stock", 0)

            if stock > 0 and size_id not in seen_stock[item_id]:
                seen_stock[item_id].add(size_id)

                link = f"https://www.sheinindia.in{url}"

                text = (
                    "🔥 *STOCK AVAILABLE*\n\n"
                    f"*Item:* {name}\n"
                    f"*Size:* Available\n"
                    f"*Link:* {link}"
                )

                app.bot.send_message(
                    chat_id=CHAT_ID,
                    text=text,
                    parse_mode="Markdown",
                    disable_web_page_preview=False,
                )

# ================= HANDLERS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Shein Verse MEN Stock Bot*\n\n"
        "⚡ Super fast stock alerts\n"
        "👕 MEN section only\n\n"
        "Use buttons below 👇",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global alerts_enabled
    query = update.callback_query
    await query.answer()

    if query.data == "on":
        alerts_enabled = True
        await query.edit_message_text(
            "🟢 *Stock Alerts ENABLED*",
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )

    elif query.data == "off":
        alerts_enabled = False
        await query.edit_message_text(
            "🔴 *Stock Alerts DISABLED*",
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )

    elif query.data == "status":
        status = "🟢 ON" if alerts_enabled else "🔴 OFF"
        await query.edit_message_text(
            f"📊 *Bot Status*\n\n"
            f"Alerts: {status}\n"
            f"Bot: 🟢 Alive & Running",
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )

# ================= MAIN =================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    scheduler = BackgroundScheduler()
    scheduler.add_job(stock_job, "interval", seconds=CHECK_INTERVAL, args=[app])
    scheduler.start()

    logging.info("✅ Bot started (Railway stable, single instance)")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
