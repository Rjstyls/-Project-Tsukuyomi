import os
import time
import requests
from openai import OpenAI
from huggingface_hub import InferenceClient
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")

if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

if HF_TOKEN:
    hf_client = InferenceClient(token=HF_TOKEN)

def perplexity_query(prompt):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "sonar-small-chat",
        "messages": [{"role": "user", "content": prompt}]
    }
    r = requests.post(url, json=data, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

async def get_ai_response(prompt):

    if OPENAI_API_KEY:
        try:
            start = time.time()
            r = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            return f"🔵 OpenAI ({round(time.time()-start,2)}s)\n\n{r.choices[0].message.content}"
        except Exception as e:
            print("OpenAI error:", e)

    if PERPLEXITY_API_KEY:
        try:
            start = time.time()
            r = perplexity_query(prompt)
            return f"🟣 Perplexity ({round(time.time()-start,2)}s)\n\n{r}"
        except Exception as e:
            print("Perplexity error:", e)

    if HF_TOKEN:
        try:
            start = time.time()
            r = hf_client.text_generation(
                prompt,
                model="mistralai/Mistral-7B-Instruct-v0.2",
                max_new_tokens=300
            )
            return f"🟡 HuggingFace ({round(time.time()-start,2)}s)\n\n{r}"
        except Exception as e:
            print("HF error:", e)

    return "⚠️ All AI providers failed."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌙 Project Tsukuyomi Activated.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Thinking...")
    reply = await get_ai_response(update.message.text)
    await update.message.reply_text(reply)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
