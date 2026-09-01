"""
Main entry point for the GitHub Codespace Controller Telegram Bot
"""
import logging
import asyncio
import os
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram import Update

from bot.handlers import start_handler, codespace_handler, github_handler, settings_handler
from database.db import db

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Initialize bot after creation"""
    await db.connect()
    logger.info("✅ Database initialized")


async def post_shutdown(application: Application) -> None:
    """Clean up before shutdown"""
    await db.disconnect()
    logger.info("Database connection closed")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors"""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ An error occurred. Please try again later."
        )


def main():
    """Start the bot"""
    # Get token from environment
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("❌ TELEGRAM_BOT_TOKEN environment variable is not set")

    # Create application
    application = Application.builder().token(token).build()
    
    # Set post init and shutdown handlers
    application.post_init = post_init
    application.post_shutdown = post_shutdown

    # Add command handlers
    application.add_handler(CommandHandler("start", start_handler.start_command))
    application.add_handler(CommandHandler("help", start_handler.help_command))
    application.add_handler(CommandHandler("myapps", start_handler.list_apps))
    application.add_handler(CommandHandler("settings", settings_handler.settings_command))
    
    # Add callback query handlers
    application.add_handler(CallbackQueryHandler(start_handler.handle_create_app, pattern="^create_app$"))
    application.add_handler(CallbackQueryHandler(start_handler.handle_main_menu, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(github_handler.set_github_repo, pattern="^set_repo_"))
    application.add_handler(CallbackQueryHandler(github_handler.set_env_vars, pattern="^set_env_"))
    application.add_handler(CallbackQueryHandler(github_handler.set_build_cmd, pattern="^set_build_"))
    application.add_handler(CallbackQueryHandler(github_handler.set_start_cmd, pattern="^set_start_"))
    application.add_handler(CallbackQueryHandler(github_handler.set_docker, pattern="^set_docker_"))
    application.add_handler(CallbackQueryHandler(github_handler.handle_docker_choice, pattern="^docker_"))
    application.add_handler(CallbackQueryHandler(codespace_handler.start_codespace, pattern="^start_codespace_"))
    application.add_handler(CallbackQueryHandler(codespace_handler.stop_codespace, pattern="^stop_codespace_"))
    application.add_handler(CallbackQueryHandler(codespace_handler.check_status, pattern="^check_status_"))
    application.add_handler(CallbackQueryHandler(settings_handler.manage_tokens, pattern="^manage_tokens$"))
    application.add_handler(CallbackQueryHandler(settings_handler.view_billing, pattern="^view_billing$"))
    application.add_handler(CallbackQueryHandler(settings_handler.add_token, pattern="^add_token$"))
    
    # Add message handlers for text input
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start_handler.handle_user_input))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, settings_handler.handle_token_input))

    # Add error handler
    application.add_error_handler(error_handler)

    logger.info("🤖 GitHub Codespace Controller Bot starting...")
    
    # Start the bot - application.run_polling() manages its own event loop
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⏹️  Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {str(e)}")
        raise
