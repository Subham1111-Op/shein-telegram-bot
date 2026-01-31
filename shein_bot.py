import os
import asyncio
import logging
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ================== ENV ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("BOT_TOKEN / CHAT_ID missing")

# ================== CONFIG ==================
CHECK_INTERVAL = 5  # SUPER FAST (seconds)

SHEIN_API = (
    "https://www.sheinindia.in/api/category/"
    "sverse-5939-37961"
    "?fields=SITE&currentPage=0&pageSize=40&format=json&query=:relevance"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13)",
    "Accept": "application/json",
    "Referer": "https://www.sheinindia.in/",
}

# ================== STATE ==================
seen_keys = set()     # block duplicates (item+signal)
last_alerts = []      # show last alerts in button
client_timeout = httpx.Timeout(10.0)

# ================== LOG ==================
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")

# ================== BUTTONS ==================
def keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Check Coupon Stock", callback_data="check")],
        [InlineKeyboardButton("📦 Last Alerts", callback_data="last"),
         InlineKeyboardButton("⚙️ Status", callback_data="status")]
    ])

# ================== TELEGRAM ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 *SHEIN VERSE MEN – COUPON BOT*\n\n"
        "✅ Coupon-applied items only\n"
        "⚡ Ultra-fast scanning\n"
        "👕 MEN section only\n\n"
        "Buttons use karo 👇",
        parse_mode="Markdown",
        reply_markup=keyboard()
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "check":
        await q.edit_message_text(
            "🔍 Checking coupon-applied stock now…",
            reply_markup=keyboard()
        )
        await check_coupon_stock(context)

    elif q.data == "last":
        txt = "📦 *No alerts yet*" if not last_alerts else "📦 *Last Alerts*\n\n" + "\n".join(last_alerts[-5:])
        await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=keyboard())

    elif q.data == "status":
        await q.edit_message_text(
            f"⚙️ *Status*\n\n"
            f"🟢 Running\n"
            f"⏱ Interval: {CHECK_INTERVAL}s\n"
            f"👕 MEN only\n"
            f"📦 Tracked alerts: {len(seen_keys)}",
            parse_mode="Markdown",
            reply_markup=keyboard()
        )

# ================== COUPON DETECTION ==================
def has_coupon_signal(p: dict) -> bool:
    """
    Multi-signal coupon detection:
    1) Explicit coupon flags/labels (if present)
    2) Promo labels containing 'coupon'
    3) Price drop vs original/list price (heuristic)
    """
    # 1) Explicit flags (varies by payload)
    for k in ("couponFlag", "hasCoupon", "isCoupon"):
        if p.get(k) is True:
            return True

    # 2) Promo / tags / labels text
    for field in ("promoLabel", "promotionLabel", "tags", "labelList"):
        val = p.get(field)
        if isinstance(val, str) and "coupon" in val.lower():
            return True
        if isinstance(val, list):
            if any(isinstance(x, str) and "coupon" in x.lower() for x in val):
                return True

    # 3) Price heuristic (sale < original/list)
    sp = p.get("salePrice") or p.get("sale_price")
    op = p.get("originalPrice") or p.get("listPrice") or p.get("original_price")
    try:
        if sp is not None and op is not None and float(sp) < float(op):
            return True
    except Exception:
        pass

    return False

# ================== STOCK CHECK ==================
async def check_coupon_stock(context: ContextTypes.DEFAULT_TYPE):
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=client_timeout) as client:
            r = await client.get(SHEIN_API)

        if r.status_code != 200:
            logging.warning(f"Shein API error {r.status_code}")
            return

        products = r.json().get("info", {}).get("products", [])

        for p in products:
            pid = p.get("goods_id")
            stock = p.get("stock", 0)

            if not pid or stock <= 0:
                continue

            if not has_coupon_signal(p):
                continue  # ONLY coupon-applied

            # build a strong duplicate key
            key = f"{pid}-coupon"
            if key in seen_keys:
                continue

            seen_keys.add(key)

            name = p.get("goods_name", "Men Item")
            price = p.get("salePrice", "")
            link = "https://www.sheinindia.in/" + p.get("goods_url", "")

            msg = (
                "🎟️ *COUPON APPLIED – MEN ITEM*\n\n"
                f"👕 {name}\n"
                f"💰 {price}\n"
                f"📦 In Stock\n"
                f"🔗 {link}"
            )

            last_alerts.append(f"• {name}")
            await context.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")

    except Exception as e:
        logging.error(f"Coupon stock error: {e}")

# ================== AUTO LOOP ==================
async def auto_loop(app: Application):
    while True:
        await check_coupon_stock(app.bot_data["ctx"])
        await asyncio.sleep(CHECK_INTERVAL)

# ================== MAIN ==================
async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))

    app.bot_data["ctx"] = app

    asyncio.create_task(auto_loop(app))

    logging.info("🚀 Coupon bot started (super fast, Railway safe)")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
