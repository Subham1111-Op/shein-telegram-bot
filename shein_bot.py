import os
import time
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from apscheduler.schedulers.background import BackgroundScheduler

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

CHECK_INTERVAL = 10  # seconds (super fast but safe)

SHEIN_API = "https://www.sheinindia.in/api/category/sverse-5939-37961"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://www.sheinindia.in/"
}

# ============== LOGGING ===================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ============== GLOBAL STATE ==============
alerts_enabled = True
seen_items = set()

# ============== TELEGRAM UI ===============
def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟢 Stock Alerts ON", callback_data="on"),
            InlineKeyboardButton("🔴 Stock Alerts OFF", callback_data="off")
        ],
        [
            InlineKeyboardButton("📊 Bot Status", callback_data="status")
        ]
    ])

# ============== COMMANDS ==================
def start(update: Update, context):
    update.message.reply_text(
        "✅ *Shein Verse MEN Bot Alive*\n\n"
        "⚡ Ultra-fast stock scanning running\n"
        "🧠 Checks existing + new stock\n",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

def button_handler(update: Update, context):
    global alerts_enabled
    query = update.callback_query
    query.answer()

    if query.data == "on":
        alerts_enabled = True
        query.edit_message_text(
            "🟢 *Stock Alerts ENABLED*",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )

    elif query.data == "off":
        alerts_enabled = False
        query.edit_message_text(
            "🔴 *Stock Alerts DISABLED*",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )

    elif query.data == "status":
        status = "🟢 ON" if alerts_enabled else "🔴 OFF"
        query.edit_message_text(
            f"📊 *Bot Status*\n\n"
            f"Alerts: {status}\n"
            f"Seen items: {len(seen_items)}\n"
            f"Uptime OK ✅",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )

# ============== STOCK CHECKER ==============
def check_stock():
    global seen_items, alerts_enabled

    if not alerts_enabled:
        return

    try:
        params = {
            "fields": "SITE",
            "currentPage": 0,
            "pageSize": 40,
            "format": "json",
            "query": ":relevance"
        }

        r = requests.get(SHEIN_API, headers=HEADERS, params=params, timeout=10)
        if r.status_code != 200:
            logging.warning("Shein API blocked / status %s", r.status_code)
            return

        data = r.json()
        products = data.get("categoryGoods", [])

        for item in products:
            goods_id = item.get("goods_id")
            name = item.get("goods_name")
            link = "https://www.sheinindia.in/" + item.get("goods_url", "")
            stock = item.get("stock", 0)

            if stock > 0 and goods_id not in seen_items:
                seen_items.add(goods_id)

                message = (
                    f"🔥 *STOCK AVAILABLE*\n\n"
                    f"👕 {name}\n"
                    f"📦 Stock: {stock}\n"
                    f"🔗 [Buy Now]({link})"
                )

                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": CHAT_ID,
                        "text": message,
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": False
                    }
                )

    except Exception as e:
        logging.error("Stock check error: %s", e)

# ============== MAIN ======================
def main():
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button_handler))

    scheduler = BackgroundScheduler()
    scheduler.add_job(check_stock, "interval", seconds=CHECK_INTERVAL)
    scheduler.start()

    # startup message
    updater.bot.send_message(
        chat_id=CHAT_ID,
        text="🚀 *Shein Verse MEN Bot Deployed*\n⚡ Ultra-fast scanning started",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
