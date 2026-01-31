import os
import asyncio
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
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("BOT_TOKEN or CHAT_ID not set in environment")

MEN_API_URL = (
    "https://www.sheinindia.in/api/category/"
    "sverse-5939-37961"
    "?fields=SITE"
    "&currentPage=0"
    "&pageSize=40"
    "&format=json"
    "&query=%3Arelevance%3Agenderfilter%3AMen"
    "&facets=genderfilter%3AMen"
    "&customerType=New"
    "&platform=Desktop"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}

SCAN_INTERVAL = 10  # seconds
# ============================================

alerts_on = False
seen_items = set()
scheduler = AsyncIOScheduler()

# ================== HELPERS ==================
def fetch_men_items():
    try:
        r = requests.get(MEN_API_URL, headers=HEADERS, timeout=15)
        data = r.json()
        return data.get("info", {}).get("products", [])
    except Exception:
        return []


def extract_stock_info(product):
    sizes = []
    for sku in product.get("skus", []):
        if sku.get("stock", 0) > 0:
            size = sku.get("attrValue", "Unknown")
            sizes.append(size)
    return sizes


async def send_alert(app, text):
    await app.bot.send_message(chat_id=CHAT_ID, text=text)

# ================== STOCK JOB ==================
async def stock_job(app):
    global seen_items

    if not alerts_on:
        return

    products = fetch_men_items()

    for p in products:
        pid = p.get("goods_id")
        if not pid:
            continue

        sizes = extract_stock_info(p)
        if not sizes:
            continue

        # New stock or new item
        if pid not in seen_items:
            seen_items.add(pid)
            title = p.get("goods_name", "Men Item")
            link = f"https://www.sheinindia.in/{p.get('goods_url', '')}"

            msg = (
                "🔥 MEN STOCK ALERT\n\n"
                f"🧥 Item: {title}\n"
                f"📏 Sizes: {', '.join(sizes)}\n"
                f"🔗 Link: {link}"
            )
            await send_alert(app, msg)

# ================== COMMANDS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🟢 Stock Alerts ON", callback_data="on")],
        [InlineKeyboardButton("🔴 Stock Alerts OFF", callback_data="off")],
        [InlineKeyboardButton("📡 Bot Status", callback_data="status")],
    ]
    await update.message.reply_text(
        "🤖 Shein Verse MEN Stock Bot Ready!\nChoose option:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def test_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧪 TEST ALERT\nBot is working perfectly ✅"
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global alerts_on
    query = update.callback_query
    await query.answer()

    if query.data == "on":
        alerts_on = True
        await query.edit_message_text("🟢 Stock Alerts TURNED ON")

    elif query.data == "off":
        alerts_on = False
        await query.edit_message_text("🔴 Stock Alerts TURNED OFF")

    elif query.data == "status":
        await query.edit_message_text(
            f"📡 Bot Status\n\n"
            f"Status: ALIVE ✅\n"
            f"Stock Alerts: {'ON' if alerts_on else 'OFF'}\n"
            f"Seen Items: {len(seen_items)}"
        )

# ================== MAIN ==================
async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test_alert", test_alert))
    app.add_handler(CallbackQueryHandler(buttons))

    scheduler.add_job(
        stock_job,
        "interval",
        seconds=SCAN_INTERVAL,
        args=[app],
        max_instances=1,
    )
    scheduler.start()

    await app.initialize()
    await app.start()
    await app.bot.send_message(
        chat_id=CHAT_ID,
        text="🤖 Bot restarted successfully\nStatus: ALIVE\nAlerts: OFF",
    )
    await app.updater.start_polling()
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
