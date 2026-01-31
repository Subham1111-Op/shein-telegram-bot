import os
import logging
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ================= ENV =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("BOT_TOKEN / CHAT_ID missing")

# ================= CONFIG =================
CHECK_INTERVAL = 5  # seconds (super fast)

SHEIN_API = (
    "https://www.sheinindia.in/api/category/"
    "sverse-5939-37961"
    "?fields=SITE&currentPage=0&pageSize=40&format=json&query=:relevance"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Android)",
    "Accept": "application/json",
    "Referer": "https://www.sheinindia.in/",
}

# ================= STATE =================
seen_items = set()
last_alerts = []

logging.basicConfig(level=logging.INFO)

# ================= BUTTONS =================
def keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔍 Check Now", callback_data="check")],
            [
                InlineKeyboardButton("📦 Last Alerts", callback_data="last"),
                InlineKeyboardButton("⚙️ Status", callback_data="status"),
            ],
        ]
    )

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 *SHEIN VERSE MEN – COUPON BOT*\n\n"
        "✅ Only MEN items\n"
        "🎟️ Coupon / price-drop detect\n"
        "⚡ Super fast alerts\n\n"
        "Use buttons 👇",
        parse_mode="Markdown",
        reply_markup=keyboard(),
    )

# ================= BUTTON HANDLER =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "check":
        await q.edit_message_text("🔍 Checking stock…", reply_markup=keyboard())
        await check_stock(context)

    elif q.data == "last":
        text = "📦 *No alerts yet*"
        if last_alerts:
            text = "📦 *Last Alerts*\n\n" + "\n".join(last_alerts[-5:])
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard())

    elif q.data == "status":
        await q.edit_message_text(
            f"⚙️ *Bot Status*\n\n"
            f"🟢 Running\n"
            f"⏱ Interval: {CHECK_INTERVAL}s\n"
            f"📦 Alerts sent: {len(seen_items)}",
            parse_mode="Markdown",
            reply_markup=keyboard(),
        )

# ================= COUPON LOGIC =================
def has_coupon(p: dict) -> bool:
    sp = p.get("salePrice")
    op = p.get("originalPrice") or p.get("listPrice")
    try:
        return sp and op and float(sp) < float(op)
    except Exception:
        return False

# ================= STOCK CHECK =================
async def check_stock(context: ContextTypes.DEFAULT_TYPE):
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=10) as client:
            r = await client.get(SHEIN_API)

        if r.status_code != 200:
            return

        products = r.json().get("info", {}).get("products", [])

        for p in products:
            pid = p.get("goods_id")
            stock = p.get("stock", 0)

            if not pid or stock <= 0:
                continue

            if not has_coupon(p):
                continue

            if pid in seen_items:
                continue

            seen_items.add(pid)

            name = p.get("goods_name", "Men Item")
            price = p.get("salePrice", "")
            link = "https://www.sheinindia.in/" + p.get("goods_url", "")

            msg = (
                "🎟️ *COUPON ITEM LIVE*\n\n"
                f"👕 {name}\n"
                f"💰 {price}\n"
                f"📦 In Stock\n"
                f"🔗 {link}"
            )

            last_alerts.append(f"• {name}")
            await context.bot.send_message(
                chat_id=CHAT_ID, text=msg, parse_mode="Markdown"
            )

    except Exception as e:
        logging.error(f"Stock error: {e}")

# ================= AUTO JOB =================
async def auto_job(context: ContextTypes.DEFAULT_TYPE):
    await check_stock(context)

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))

    app.job_queue.run_repeating(auto_job, interval=CHECK_INTERVAL, first=3)

    logging.info("✅ Bot running safely (Railway compatible)")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
