"""Telegram bot. Send it a question; it edits its reply live while the agents work."""
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from querymesh import config, observability
from querymesh.api_client import format_final, get_token, stream_question

observability.setup("querymesh-telegram")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hi! I am QueryMesh. Send me a question about arXiv research.")


async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply = await update.message.reply_text("Working...")
    progress = ""
    async for kind, value in stream_question(update.message.text, get_token()):
        if kind == "step":
            progress += f"- {value}\n"
            await reply.edit_text(f"Working...\n{progress}")
        else:
            await reply.edit_text(format_final(value)[:4000])  # Telegram limit: 4096 characters


def main() -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is empty: put the token from @BotFather in .env")
    app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, answer))
    app.run_polling()


if __name__ == "__main__":
    main()
