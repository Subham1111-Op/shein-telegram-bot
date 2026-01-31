import os
import asyncio
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
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("BOT_TOKEN or CHAT_ID not set")

SHEIN_API = (
    "https://www.sheinindia.in/api/category/"
    "sverse-5939-37961"
    "?fields=SITE"
    "&currentPage=0"
    "&pageSize=40"
    "&format=json"
    "&query=%3Arelevance%3Agenderfilter%3AMen"
    "&facets=genderfilter%3AMen"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
}

CHECK_INTERVAL = 10  # seconds
alerts_enabled = True
seen_items = set()

logging.basicConfig(level=logging.INFO)

# ================= BOT UI =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🟢 Stock Alerts ON", callback_data="on")],
        [InlineKeyboardButton("🔴 Stock Alerts OFF", callback_data="off")],
        [InlineKeyboardButton("📡 Bot Status", callback_data="status")],
    ]
    await update.message.reply_text(
        "🔥 Shein Verse MEN Stock Bot Started",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global alerts_enabled
    query = update.callback_query
    await query.answer()

    if query.data == "on":
        alerts_enabled = True
        await query.edit_message_text("🟢 Stock alerts ENABLED")

    elif query.data == "off":
        alerts_enabled = False
        await query.edit_message_text("🔴 Stock alerts DISABLED")

    elif query.data == "status":
        status = "ON" if alerts_enabled else "OFF"
        await query.edit_message_text(f"📡 Bot is ALIVE\nAlerts: {status}")

# ================= STOCK CHECK =================
async def check_stock(context: ContextTypes.DEFAULT_TYPE):
    global seen_items, alerts_enabled
    if not alerts_enabled:
        return

    try:
        r = requests.get(SHEIN_API, headers=HEADERS, timeout=15)
        data = r.json()

        products = data.get("info", {}).get("products", [])

        for p in products:
            goods_id = p.get("goods_id")
            name = p.get("goods_name", "Item")
            url = "https://www.shein.in/" + p.get("goods_url", "")
            stock = p.get("stock", 0)

            if stock > 0 and goods_id not in seen_items:
                seen_items.add(goods_id)

                msg = (
                    "🔥 *MEN STOCK AVAILABLE*\n\n"
                    f"*{name}*\n"
                    f"Stock: {stock}\n"
                    f"[Open Product]({url})"
                )

                await context.bot.send_message(
                    chat_id=CHAT_ID,
                    text=msg,
                    parse_mode="Markdown",
                    disable_web_page_preview=False,
                )

    except Exception as e:
        logging.error(f"Stock check error: {e}")

# ================= MAIN =================
async def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(buttons))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_stock,
        "interval",
        seconds=CHECK_INTERVAL,
        args=[application.bot],
        max_instances=1,   # 🔥 VERY IMPORTANT (conflict fix)
        coalesce=True,
    )
    scheduler.start()

    await application.initialize()
    await application.start()
    await application.bot.initialize()

    logging.info("🤖 Bot started safely (single instance)")

    await application.stop()  # keeps process alive safely


if __name__ == "__main__":
    asyncio.run(main())
