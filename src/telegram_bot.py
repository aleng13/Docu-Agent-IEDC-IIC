"""
Telegram Bot Interface
----------------------
Handles the /create command to trigger Google Drive folder logic asyncronously.
"""

import os
import json
import logging
import asyncio
import time
from typing import Optional, Dict, Any, Callable
from dotenv import load_dotenv

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from src.drive_auth import get_drive_service
from src.folder_logic import create_event_folder

log = logging.getLogger(__name__)

# Load config and environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SHARED_DRIVE_ID = os.getenv("SHARED_DRIVE_ID")

def get_config_ids() -> Dict[str, Optional[str]]:
    """Retrieves the required folder IDs preferring config.json, with fallback to .env."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(project_root, "config.json")
    
    parent_id = os.getenv("PARENT_FOLDER_ID")
    template_id = os.getenv("TEMPLATE_FOLDER_ID")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            parent_id = parent_id or config.get("parent_folder_id")
            template_id = template_id or config.get("template_folder_id")
    except Exception as e:
        log.warning(f"Could not load from config.json: {e}")

    return {
        "parent_id": parent_id,
        "template_id": template_id
    }

async def _create_event_task(chat_id: int, event_name: str, app: Any, progress_msg_id: int) -> None:
    """Background task to heavily execute the folder creation logic."""
    log.info(f"Background: Creating folder for {event_name}")
    
    ids = get_config_ids()
    parent_id = ids["parent_id"]
    template_id = ids["template_id"]

    if not parent_id or not template_id:
        await app.bot.send_message(chat_id, "❌ *Config Error:* Missing parent_id or template_id.")
        return

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    loop = asyncio.get_event_loop()
    last_update_time = [0.0]  # Use a list for mutability in closure

    def on_progress_callback(status: str) -> None:
        """Throttled callback to update Telegram message from worker thread."""
        now = time.time()
        if now - last_update_time[0] < 1.0:
            return
        last_update_time[0] = now
        
        # Schedule the async edit_message_text in the main loop
        asyncio.run_coroutine_threadsafe(
            app.bot.edit_message_text(
                chat_id=chat_id,
                message_id=progress_msg_id,
                text=f"🚀 *Creating folder for {event_name}...*\n🔄 {status}",
                parse_mode=ParseMode.MARKDOWN
            ),
            loop
        )

    try:
        service = get_drive_service(project_root)
        
        # Run synchronous folder creation in a background thread
        folder_id = await asyncio.to_thread(
            create_event_folder,
            service=service,
            event_name=event_name,
            template_id=template_id,
            parent_id=parent_id,
            shared_drive_id=SHARED_DRIVE_ID,
            on_progress=on_progress_callback
        )
        
        if folder_id:
            link = f"https://drive.google.com/drive/folders/{folder_id}"
            text = f"✅ *Folder Created!*\n📂 Event: `{event_name}`\n🔗 {link}"
        else:
            text = f"❌ *Failed:* Could not create folder (check terminal logs or idempotency check)."
    except Exception as e:
        log.error(f"Create Error: {e}")
        text = f"❌ *Error:* {str(e)}"

    # Final update (not using the callback so no throttling)
    await app.bot.edit_message_text(
        chat_id=chat_id,
        message_id=progress_msg_id, 
        text=text, 
        parse_mode=ParseMode.MARKDOWN
    )

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point check command."""
    if update.effective_message:
         await update.effective_message.reply_text("👋 Hello! I am the Docu-Agent Bot.\nUsage: `/create <EventName>`", parse_mode=ParseMode.MARKDOWN)

async def create_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Triggered on /create."""
    if not update.effective_message or not update.effective_chat: 
        return
        
    if not context.args: 
        await update.effective_message.reply_text("⚠️ Usage: `/create <EventName>`", parse_mode=ParseMode.MARKDOWN)
        return
        
    event_name = " ".join(context.args)
    msg = await update.effective_message.reply_text(f"🚀 Creating folder for *{event_name}*...", parse_mode=ParseMode.MARKDOWN)
    
    # Spawn background task
    context.application.create_task(_create_event_task(update.effective_chat.id, event_name, context.application, msg.message_id))

def main() -> None:
    """Startup for the Telegram Bot."""
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN is missing in the .env file.")
        
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("create", create_cmd))
    
    log.info("🤖 Bot is starting up in POLLING mode...")
    app.run_polling()

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    main()
