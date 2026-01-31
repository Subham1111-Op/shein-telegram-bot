import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from apscheduler.schedulers.background import BackgroundScheduler

# ================== ENV ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("BOT_TOKEN or CHAT_ID missing")

CHAT_ID = int(CHAT_ID)

# ================== CONFIG ==================
MEN_API_URL = (
    "https://www.sheinindia.in/api/category/"
    "sverse-5939-37961"
    "?fields=SITE&currentPage=0&pageSize=40&format=json"
    "&query=:relevance:genderfilter:Men"
)

CHECK_INTERVAL = 10  # seconds

alerts_enabled = False
seen_products = set()

# ================== TELEGRAM HANDLERS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🟢 Stock Alerts ON", callback_data="ON")],
        [InlineKeyboardButton("🔴 Stock Alerts OFF", callback_data="OFF")],
    ]
    await update.message.reply_text(
        "🤖 *Shein Verse MEN Stock Bot*\n\n"
        "• Fast stock alerts\n"
        "• Only MEN items\n"
        "• Any size stock\n\n"
        "Choose an option 👇",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global alerts_enabled
    query = update.callback_query
    await query.answer()

    if query.data == "ON":
        alerts_enabled = True
        await query.edit_message_text("🟢 Stock Alerts ENABLED")
    elif query.data == "OFF":
        alerts_enabled = False
        await query.edit_message_text("🔴 Stock Alerts DISABLED")

# ================== STOCK CHECK ==================
def check_stock():
    if not alerts_enabled:
        return

    try:
        res = requests.get(MEN_API_URL, timeout=15)
        data = res.json()

        products = data.get("info", {}).get("products", [])

        for p in products:
            product_id = p.get("goods_id")
            stock = p.get("stock", 0)

            if stock > 0 and product_id not in seen_products:
                seen_products.add(product_id)

                name = p.get("goods_name", "Unknown Item")
                link = f"https://www.sheinindia.in/{p.get('goods_url_name','')}"

                message = (
                    "🔥 *STOCK AVAILABLE*\n\n"
                    f"*{name}*\n"
                    f"Stock: {stock}\n\n"
                    f"{link}"
                )

                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": CHAT_ID,
                        "text": message,
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": False,
                    },
                    timeout=10,
                )

    except Exception as e:
        print("Stock check error:", e)

# ================== MAIN ==================
def main():
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .concurrent_updates(False)  # IMPORTANT for Railway
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    scheduler = BackgroundScheduler()
    scheduler.add_job(check_stock, "interval", seconds=CHECK_INTERVAL)
    scheduler.start()

    print("✅ Bot started safely (Railway stable)")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
