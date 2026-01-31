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
CHAT_ID = int(os.getenv("CHAT_ID"))

CHECK_INTERVAL = 10  # seconds

# SHEIN VERSE MEN API (MEN ONLY)
SHEIN_MEN_API = (
    "https://www.sheinindia.in/api/category/sverse-5939-37961"
    "?fields=SITE&currentPage=0&pageSize=40&format=json"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}

# ================= LOGGING =================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# ================= STATE =================

alerts_on = False
seen_items = set()

# ================= BOT COMMANDS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🟢 Stock Alerts ON", callback_data="on")],
        [InlineKeyboardButton("🔴 Stock Alerts OFF", callback_data="off")],
        [InlineKeyboardButton("📡 Bot Status", callback_data="status")],
    ]

    await update.message.reply_text(
        "🤖 *Shein Verse MEN Stock Bot Ready!*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global alerts_on

    query = update.callback_query
    await query.answer()

    if query.data == "on":
        alerts_on = True
        await query.edit_message_text("🟢 *Stock Alerts TURNED ON!*", parse_mode="Markdown")

    elif query.data == "off":
        alerts_on = False
        await query.edit_message_text("🔴 *Stock Alerts TURNED OFF!*", parse_mode="Markdown")

    elif query.data == "status":
        status_text = (
            f"📡 *Bot Status*\n\n"
            f"Status: 🟢 RUNNING\n"
            f"Alerts: {'ON' if alerts_on else 'OFF'}\n"
            f"Seen Items: {len(seen_items)}"
        )
        await query.edit_message_text(status_text, parse_mode="Markdown")


# ================= STOCK CHECK =================

async def check_stock(bot):
    global alerts_on

    if not alerts_on:
        return

    try:
        r = requests.get(SHEIN_MEN_API, headers=HEADERS, timeout=15)
        data = r.json()

        items = data.get("info", {}).get("products", [])

        for item in items:
            item_id = item.get("goods_id")
            name = item.get("goods_name")
            stock = item.get("stock", 0)
            url = "https://www.sheinindia.in/" + item.get("goods_url", "")

            if stock > 0 and item_id not in seen_items:
                seen_items.add(item_id)

                msg = (
                    f"🔥 *MEN ITEM IN STOCK!*\n\n"
                    f"👕 {name}\n"
                    f"📦 Stock: {stock}\n"
                    f"🔗 {url}"
                )

                await bot.send_message(
                    chat_id=CHAT_ID,
                    text=msg,
                    parse_mode="Markdown",
                )

    except Exception as e:
        logging.error(f"Stock check error: {e}")


# ================= MAIN =================

async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN not set")

    if not CHAT_ID:
        raise RuntimeError("CHAT_ID not set")

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(buttons))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_stock,
        "interval",
        seconds=CHECK_INTERVAL,
        args=[application.bot],
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()

    await application.initialize()
    await application.start()
    await application.bot.initialize()

    logging.info("🤖 Bot started safely (Railway stable)")

    # 🔥 KEEP PROCESS ALIVE
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
