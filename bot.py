import os
import time
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
from huggingface_hub import InferenceClient

# ================= ENV =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# ================= AI SETUP =================

if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

if HF_TOKEN:
    hf_client = InferenceClient(token=HF_TOKEN)

# ================= AI RESPONSE =================

async def get_ai_response(prompt):

    # OpenAI
    if OPENAI_API_KEY:
        try:
            start = time.time()
            r = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            return f"🔵 OpenAI ({round(time.time()-start,2)}s)\n\n{r.choices[0].message.content}"
        except:
            pass

    # HuggingFace fallback
    if HF_TOKEN:
        try:
            start = time.time()
            r = hf_client.text_generation(
                prompt,
                model="mistralai/Mistral-7B-Instruct-v0.2",
                max_new_tokens=200
            )
            return f"🟡 HuggingFace ({round(time.time()-start,2)}s)\n\n{r}"
        except:
            pass

    return "⚠️ All AI providers failed."

# ================= TELEGRAM =================

telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌙 Project Tsukuyomi Webhook Mode Active.")

async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID and update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("✅ Bot Running.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Thinking...")
    reply = await get_ai_response(update.message.text)
    await update.message.reply_text(reply)

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("health", health))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ================= FLASK WEBHOOK =================

app = Flask(__name__)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return "OK"

@app.route("/")
def home():
    return "Bot is running!"

if __name__ == "__main__":
    telegram_app.initialize()
    telegram_app.start()
    PORT = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=PORT)
