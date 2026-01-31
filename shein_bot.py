import os
import time
import requests
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

CHECK_INTERVAL = 5  # ⚡ fastest SAFE speed
alerts_enabled = False

SEEN_ITEMS = set()
STOCK_ITEMS = set()

SHEIN_API = "https://www.sheinindia.in/api/category/sverse-5939-37961"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://www.sheinindia.in/"
}

PARAMS = {
    "fields": "SITE",
    "currentPage": 0,
    "pageSize": 40,
    "format": "json",
    "query": ":relevance",
}

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("SHEIN-VERSE-BOT")

# ================= UI =================
def keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Stock Alerts ON", callback_data="on")],
        [InlineKeyboardButton("🔴 Stock Alerts OFF", callback_data="off")],
        [InlineKeyboardButton("📊 Bot Status", callback_data="status")]
    ])

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🔥 *Shein Verse MEN Pro Bot*\n\n"
        "✅ Existing stock alerts\n"
        "✅ New item alerts\n"
        "✅ Super fast scan\n\n"
        "Controls 👇",
        parse_mode="Markdown",
        reply_markup=keyboard()
    )

def buttons(update: Update, context: CallbackContext):
    global alerts_enabled
    q = update.callback_query
    q.answer()

    if q.data == "on":
        alerts_enabled = True
        q.edit_message_text("🟢 Alerts ENABLED", reply_markup=keyboard())

    elif q.data == "off":
        alerts_enabled = False
        q.edit_message_text("🔴 Alerts DISABLED", reply_markup=keyboard())

    elif q.data == "status":
        q.edit_message_text(
            f"📊 *Bot Status*\n\n"
            f"Alerts: {'ON 🟢' if alerts_enabled else 'OFF 🔴'}\n"
            f"Seen Items: {len(SEEN_ITEMS)}\n"
            f"In Stock: {len(STOCK_ITEMS)}",
            parse_mode="Markdown",
            reply_markup=keyboard()
        )

# ================= CORE =================
def scan_stock():
    if not alerts_enabled:
        return

    try:
        r = requests.get(
            SHEIN_API,
            headers=HEADERS,
            params=PARAMS,
            timeout=10
        )

        if r.status_code != 200:
            log.warning("Shein blocked (403)")
            return

        products = r.json().get("info", {}).get("products", [])

        for p in products:
            pid = p.get("goods_id")
            name = p.get("goods_name")
            stock = p.get("availableStock", 0)
            url = "https://www.sheinindia.in/" + p.get("goods_url", "")

            if not pid:
                continue

            # NEW ITEM
            if pid not in SEEN_ITEMS:
                SEEN_ITEMS.add(pid)
                send_msg(
                    f"🆕 *NEW VERSE MEN ITEM*\n\n"
                    f"*{name}*\n\n"
                    f"🔗 {url}"
                )

            # STOCK AVAILABLE
            if stock > 0 and pid not in STOCK_ITEMS:
                STOCK_ITEMS.add(pid)
                send_msg(
                    f"⚡ *STOCK LIVE*\n\n"
                    f"*{name}*\n"
                    f"📦 Stock: {stock}\n\n"
                    f"🔗 {url}"
                )

            # RESET IF OOS
            if stock == 0 and pid in STOCK_ITEMS:
                STOCK_ITEMS.remove(pid)

    except Exception as e:
        log.error(f"Scan error: {e}")

def send_msg(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": "Markdown"
            },
            timeout=10
        )
    except:
        pass

# ================= MAIN =================
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(buttons))

    scheduler = BackgroundScheduler()
    scheduler.add_job(scan_stock, "interval", seconds=CHECK_INTERVAL)
    scheduler.start()

    log.info("✅ BOT RUNNING (PRO MODE)")

    updater.start_polling(drop_pending_updates=True)
    updater.idle()

if __name__ == "__main__":
    main()
