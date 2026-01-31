import os
import asyncio
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("BOT_TOKEN or CHAT_ID not set in environment")

SHEIN_API = (
    "https://www.sheinindia.in/api/category/"
    "sverse-5939-37961?"
    "currentPage=0&pageSize=40&format=json"
    "&query=%3Arelevance%3Agenderfilter%3AMen"
    "&facets=genderfilter%3AMen"
    "&customerType=New"
)

CHECK_INTERVAL = 10  # seconds (super fast)

# ================= GLOBAL STATE =================

alerts_enabled = False
seen_items = set()

# ================= LOGGING =================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# ================= HELPERS =================

def fetch_products():
    try:
        r = requests.get(SHEIN_API, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("info", {}).get("products", [])
    except Exception as e:
        logging.error(f"Shein API error: {e}")
        return []


def product_has_stock(product):
    for sku in product.get("sku_list", []):
        if sku.get("stock", 0) > 0:
            return True
    return False


def product_link(product):
    goods_id = product.get("goods_id")
    return f"https://www.sheinindia.in/product-p-{goods_id}.html"


# ================= BOT HANDLERS =================

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


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global alerts_enabled
    query = update.callback_query
    await query.answer()

    if query.data == "on":
        alerts_enabled = True
        await query.edit_message_text("🟢 Stock Alerts TURNED ON")

    elif query.data == "off":
        alerts_enabled = False
        await query.edit_message_text("🔴 Stock Alerts TURNED OFF")

    elif query.data == "status":
        msg = (
            f"📡 *Bot Status*\n\n"
            f"Status: 🟢 RUNNING\n"
            f"Alerts: {'ON' if alerts_enabled else 'OFF'}\n"
            f"Seen Items: {len(seen_items)}"
        )
        await query.edit_message_text(msg, parse_mode="Markdown")


# ================= STOCK CHECK JOB =================

async def check_stock(context: ContextTypes.DEFAULT_TYPE):
    if not alerts_enabled:
        return

    products = fetch_products()

    for product in products:
        pid = product.get("goods_id")
        name = product.get("goods_name")

        if not pid:
            continue

        in_stock = product_has_stock(product)

        if in_stock and pid not in seen_items:
            seen_items.add(pid)

            msg = (
                f"🔥 *STOCK AVAILABLE!*\n\n"
                f"👕 {name}\n"
                f"🔗 {product_link(product)}"
            )

            await context.bot.send_message(
                chat_id=CHAT_ID,
                text=msg,
                parse_mode="Markdown",
                disable_web_page_preview=False,
            )


# ================= MAIN =================

async def main():
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .concurrent_updates(False)  # 🔒 SINGLE INSTANCE SAFE
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_stock,
        "interval",
        seconds=CHECK_INTERVAL,
        args=[app.bot],
    )
    scheduler.start()

    logging.info("🤖 Bot started safely (stable mode)")
    await app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
