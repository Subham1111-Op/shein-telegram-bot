import os
import aiohttp
import logging
from typing import Set

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ================== CONFIG ==================

BOT_TOKEN = os.getenv("BOT_TOKEN")

CHAT_ID = 7855120289   # ✅ MANUAL CHAT ID

BASE_URL = "https://www.sheinindia.in/api/category/sverse-5939-37961"

PAGES_TO_SCAN = 4
CHECK_INTERVAL = 8   # seconds (super fast)

ALERTS_ON = False

seen_products: Set[str] = set()
seen_instock: Set[str] = set()

logging.basicConfig(level=logging.INFO)

# ================== UI ==================

def build_menu():
    keyboard = [
        [InlineKeyboardButton("🟢 Stock Alerts ON", callback_data="on")],
        [InlineKeyboardButton("🔴 Stock Alerts OFF", callback_data="off")],
        [InlineKeyboardButton("📡 Bot Status", callback_data="status")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ================== API ==================

async def fetch_page(session, page: int):
    params = {
        "fields": "SITE",
        "currentPage": page,
        "pageSize": 40,
        "format": "json",
        "query": ":relevance:genderfilter:Men",
        "facets": "genderfilter:Men",
        "platform": "Desktop",
    }
    async with session.get(BASE_URL, params=params, timeout=20) as resp:
        return await resp.json()

# ================== BOT COMMANDS ==================

async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Shein Verse PRO FAST Bot Ready!\nChoose option:",
        reply_markup=build_menu()
    )

async def button_handler(update, context: ContextTypes.DEFAULT_TYPE):
    global ALERTS_ON
    query = update.callback_query
    await query.answer()

    if query.data == "on":
        ALERTS_ON = True
        await query.edit_message_text(
            "🟢 SUPER FAST Stock Alerts TURNED ON!",
            reply_markup=build_menu()
        )

    elif query.data == "off":
        ALERTS_ON = False
        await query.edit_message_text(
            "🔴 Stock Alerts TURNED OFF!",
            reply_markup=build_menu()
        )

    elif query.data == "status":
        await query.edit_message_text(
            f"🤖 Bot Status:\n"
            f"Status: 🟢 ALIVE & RUNNING\n"
            f"Stock Alerts: {'ON' if ALERTS_ON else 'OFF'}\n"
            f"Seen Items: {len(seen_products)}",
            reply_markup=build_menu()
        )

# ================== STOCK SCANNER ==================

async def stock_job(context: ContextTypes.DEFAULT_TYPE):
    global ALERTS_ON, seen_products, seen_instock

    if not ALERTS_ON:
        return

    bot = context.application.bot

    if not hasattr(context.application, "http_session"):
        context.application.http_session = aiohttp.ClientSession()

    session = context.application.http_session

    try:
        for page in range(PAGES_TO_SCAN):
            data = await fetch_page(session, page)
            products = data.get("info", {}).get("products", [])

            for p in products:
                product_id = str(p.get("goods_id"))
                name = p.get("goods_name", "Unknown")
                price = p.get("salePrice", "")
                url = p.get("goods_url", "")

                # ---------- NEW PRODUCT ----------
                if product_id not in seen_products:
                    seen_products.add(product_id)
                    await bot.send_message(
                        chat_id=CHAT_ID,
                        text=(
                            "🆕 NEW PRODUCT ADDED!\n\n"
                            f"👕 {name}\n"
                            f"💰 {price}\n"
                            f"🔗 {url}"
                        )
                    )

                # ---------- STOCK CHECK (ANY SIZE) ----------
                in_stock = False

                if isinstance(p.get("stock"), int) and p.get("stock", 0) > 0:
                    in_stock = True

                if p.get("isSoldOut") is False:
                    in_stock = True

                if in_stock and product_id not in seen_instock:
                    seen_instock.add(product_id)
                    await bot.send_message(
                        chat_id=CHAT_ID,
                        text=(
                            "🔥 STOCK AVAILABLE!\n\n"
                            f"👕 {name}\n"
                            f"💰 {price}\n"
                            f"🔗 {url}\n\n"
                            "⚡ ANY SIZE STOCK DETECTED!"
                        )
                    )

    except Exception as e:
        logging.exception("Stock job error")
        await bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Scanner error: {e}")

# ================== MAIN (STABLE) ==================

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN not set in environment")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.job_queue.run_repeating(stock_job, interval=CHECK_INTERVAL, first=5)

    print("🚀 Shein Verse PRO FAST Bot started")

    app.run_polling()

if __name__ == "__main__":
    main()
