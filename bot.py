import os
import asyncio
import time
import requests
import google.generativeai as genai
from openai import OpenAI
from huggingface_hub import InferenceClient
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ================= ENV =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # optional

# ================= AI SETUP =================

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-1.5-flash")

if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

if HF_TOKEN:
    hf_client = InferenceClient(token=HF_TOKEN)

# ================= PERPLEXITY =================

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

# ================= SMART FALLBACK =================

async def get_ai_response(prompt):

    providers = []

    if GEMINI_API_KEY:
        providers.append("gemini")
    if OPENAI_API_KEY:
        providers.append("openai")
    if PERPLEXITY_API_KEY:
        providers.append("perplexity")
    if HF_TOKEN:
        providers.append("hf")

    for provider in providers:
        try:
            start_time = time.time()

            if provider == "gemini":
                r = gemini_model.generate_content(prompt)
                if r.text:
                    return f"🟢 Gemini ({round(time.time()-start_time,2)}s)\n\n{r.text}"

            elif provider == "openai":
                r = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                return f"🔵 OpenAI ({round(time.time()-start_time,2)}s)\n\n{r.choices[0].message.content}"

            elif provider == "perplexity":
                r = perplexity_query(prompt)
                return f"🟣 Perplexity ({round(time.time()-start_time,2)}s)\n\n{r}"

            elif provider == "hf":
                r = hf_client.text_generation(
                    prompt,
                    model="mistralai/Mistral-7B-Instruct-v0.2",
                    max_new_tokens=300
                )
                return f"🟡 HuggingFace ({round(time.time()-start_time,2)}s)\n\n{r}"

        except Exception as e:
            print(f"{provider} failed:", e)
            continue

    return "⚠️ All AI providers failed."

# ================= COMMANDS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌙 Project Tsukuyomi Activated.\nSend a message.")

async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if ADMIN_ID and update.effective_user.id != ADMIN_ID:
        return

    status = ""
    status += f"Gemini: {'✅' if GEMINI_API_KEY else '❌'}\n"
    status += f"OpenAI: {'✅' if OPENAI_API_KEY else '❌'}\n"
    status += f"Perplexity: {'✅' if PERPLEXITY_API_KEY else '❌'}\n"
    status += f"HuggingFace: {'✅' if HF_TOKEN else '❌'}\n"

    await update.message.reply_text("🔍 API Health\n\n" + status)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Thinking...")
    reply = await get_ai_response(update.message.text)
    await update.message.reply_text(reply)

# ================= ERROR HANDLER =================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print("Global Error:", context.error)

# ================= RUN =================

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("health", health))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_error_handler(error_handler)

print("🌙 Project Tsukuyomi Phase 1 Running...")
app.run_polling()
