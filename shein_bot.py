import os
import requests
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    CallbackContext,
)
from apscheduler.schedulers.background import BackgroundScheduler

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

CHECK_INTERVAL = 3  # ⚡ ultra fast (safe)
ALERTS_ENABLED = True

SEEN_ITEMS = set()
STOCK_ITEMS = set()

SHEIN_API = "https://www.sheinindia.in/api/category/sverse-5939-37961"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
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

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("SHEIN-VERSE-BOT")

# ================= UI =================
def keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Stock Alerts ON", callback_data="on")],
        [InlineKeyboardButton("🔴 Stock Alerts OFF", callback_data="off")],
        [InlineKeyboardButton("📊 Bot Status", callback_data="status")],
    ])

# ================= COMMANDS =================
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🚀 *SHEIN VERSE MEN STOCK BOT LIVE*\n\n"
        "⚡ Ultra-fast scanning enabled\n"
        "📦 Existing + New stock alerts\n\n"
        "Controls 👇",
        parse_mode="Markdown",
        reply_markup=keyboard(),
    )

def buttons(update: Update, context: CallbackContext):
    global ALERTS_ENABLED
    q = update.callback_query
    q.answer()

    if q.data == "on":
        ALERTS_ENABLED = True
        q.edit_message_text("🟢 *Stock Alerts ENABLED*", parse_mode="Markdown", reply_markup=keyboard())

    elif q.data == "off":
        ALERTS_ENABLED = False
        q.edit_message_text("🔴 *Stock Alerts DISABLED*", parse_mode="Markdown", reply_markup=keyboard())

    elif q.data == "status":
        q.edit_message_text(
            f"📊 *Bot Status*\n\n"
            f"🟢 Alive: YES\n"
            f"🔔 Alerts: {'ON' if ALERTS_ENABLED else 'OFF'}\n"
            f"👕 Items Seen: {len(SEEN_ITEMS)}\n"
            f"📦 In Stock Tracked: {len(STOCK_ITEMS)}",
            parse_mode="Markdown",
            reply_markup=keyboard(),
        )

# ================= CORE LOGIC =================
def scan_stock():
    if not ALERTS_ENABLED:
        return

    try:
        r = requests.get(SHEIN_API, headers=HEADERS, params=PARAMS, timeout=8)

        if r.status_code != 200:
            log.warning("Shein blocked / error")
            return

        products = r.json().get("info", {}).get("products", [])

        for p in products:
            pid = p.get("goods_id")
            name = p.get("goods_name")
            url = "https://www.sheinindia.in/" + p.get("goods_url", "")
            stock = p.get("availableStock", 0)

            if not pid:
                continue

            # NEW ITEM
            if pid not in SEEN_ITEMS:
                SEEN_ITEMS.add(pid)
                if stock > 0:
                    send_alert(
                        f"🆕 *NEW MEN ITEM IN STOCK*\n\n"
                        f"*{name}*\n"
                        f"📦 Stock: {stock}\n\n"
                        f"🔗 {url}"
                    )
                    STOCK_ITEMS.add(pid)

            # RESTOCK
            elif stock > 0 and pid not in STOCK_ITEMS:
                STOCK_ITEMS.add(pid)
                send_alert(
                    f"🔥 *RESTOCK ALERT*\n\n"
                    f"*{name}*\n"
                    f"📦 Stock: {stock}\n\n"
                    f"🔗 {url}"
                )

            # OUT OF STOCK RESET
            elif stock == 0 and pid in STOCK_ITEMS:
                STOCK_ITEMS.remove(pid)

    except Exception as e:
        log.error(f"Scan error: {e}")

def send_alert(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False,
            },
            timeout=10,
        )
    except Exception as e:
        log.error(f"Telegram error: {e}")

# ================= MAIN =================
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(buttons))

    scheduler = BackgroundScheduler()
    scheduler.add_job(scan_stock, "interval", seconds=CHECK_INTERVAL)
    scheduler.start()

    # 🔥 Deploy hote hi message
    send_alert("✅ *Shein Verse MEN Bot Deployed & Alive*\n\n⚡ Ultra-fast stock scanning started")

    log.info("🚀 BOT RUNNING (ULTRA FAST MODE)")
    updater.start_polling(drop_pending_updates=True)
    updater.idle()

if __name__ == "__main__":
    main()
