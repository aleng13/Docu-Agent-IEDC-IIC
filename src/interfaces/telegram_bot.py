"""
Telegram Bot Interface
----------------------
Handles the /create command to trigger Google Drive folder logic asynchronously.
"""

import os
import json
import logging
import asyncio
import time
import html
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from src.core.drive_auth import get_drive_service
from src.core.config import get_project_root
from src.tools.folder_logic import create_event_folder
from src.interfaces.keep_alive import keep_alive

log = logging.getLogger(__name__)

# Load config and environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SHARED_DRIVE_ID = os.getenv("SHARED_DRIVE_ID")


def get_config_ids() -> Dict[str, Optional[str]]:
    """Retrieves the required folder IDs preferring config.json, with fallback to .env.

    Returns:
        Dict[str, Optional[str]]: Parent and template folder IDs.
    """
    project_root = get_project_root()
    config_path = os.path.join(project_root, "config.json")

    parent_id = os.getenv("PARENT_FOLDER_ID")
    template_id = os.getenv("TEMPLATE_FOLDER_ID")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            parent_id = parent_id or config.get("parent_folder_id")
            template_id = template_id or config.get("template_folder_id")
    except Exception as e:
        log.warning("Could not load from config.json: %s", e)

    return {"parent_id": parent_id, "template_id": template_id}


async def _create_event_task(chat_id: int, event_name: str, app: Application, progress_msg_id: int) -> None:
    """Background task to execute folder creation logic.

    Args:
        chat_id: Target Telegram chat ID.
        event_name: Event name received from the user.
        app: Telegram application instance.
        progress_msg_id: Message ID used for progress updates.

    Returns:
        None
    """
    try:
        log.info("Background: Creating folder for %s", event_name)
        safe_event_name = html.escape(event_name)

        ids = get_config_ids()
        parent_id = ids["parent_id"]
        template_id = ids["template_id"]

        if not parent_id or not template_id:
            await app.bot.send_message(
                chat_id=chat_id,
                text="❌ <b>Config Error:</b> Missing parent_id or template_id.",
                parse_mode=ParseMode.HTML,
            )
            return

        project_root = get_project_root()
        loop = asyncio.get_event_loop()
        last_update_time = [0.0]  # Mutable timestamp holder for throttling.

        def on_progress_callback(status: str) -> None:
            """Throttled callback to update Telegram message from worker thread.

            Args:
                status: Human-readable progress text.

            Returns:
                None
            """
            now = time.time()
            if now - last_update_time[0] < 1.0:
                return
            last_update_time[0] = now

            safe_status = html.escape(status)
            asyncio.run_coroutine_threadsafe(
                app.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=progress_msg_id,
                    text=f"<b>Creating folder for {safe_event_name}...</b>\n{safe_status}",
                    parse_mode=ParseMode.HTML,
                ),
                loop,
            )

        service = get_drive_service(project_root)
        folder_id = await asyncio.to_thread(
            create_event_folder,
            service=service,
            event_name=event_name,
            template_id=template_id,
            parent_id=parent_id,
            shared_drive_id=SHARED_DRIVE_ID,
            on_progress=on_progress_callback,
        )

        if folder_id:
            link = f"https://drive.google.com/drive/folders/{folder_id}"
            text = (
                "<b>Folder Created!</b>\n"
                f"Event: <code>{safe_event_name}</code>\n"
                f"<a href=\"{html.escape(link, quote=True)}\">Open Folder</a>"
            )
        else:
            text = "❌ <b>Failed:</b> Could not create folder (check terminal logs or idempotency check)."

        await app.bot.edit_message_text(
            chat_id=chat_id,
            message_id=progress_msg_id,
            text=text,
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        log.exception("Unhandled error in _create_event_task")
        await app.bot.send_message(
            chat_id=chat_id,
            text=f"❌ <b>Critical Error:</b> {html.escape(str(e))}",
            parse_mode=ParseMode.HTML,
        )


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point check command.

    Args:
        update: Incoming Telegram update.
        context: Telegram callback context.

    Returns:
        None
    """
    del context
    if update.effective_message:
        await update.effective_message.reply_text(
            "Hello! I am the Docu-Agent Bot.\nUsage: <code>/create &lt;EventName&gt;</code>",
            parse_mode=ParseMode.HTML,
        )


async def create_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Triggered on /create.

    Args:
        update: Incoming Telegram update.
        context: Telegram callback context.

    Returns:
        None
    """
    try:
        if not update.effective_message or not update.effective_chat:
            return

        if not context.args:
            await update.effective_message.reply_text(
                "Usage: <code>/create &lt;EventName&gt;</code>",
                parse_mode=ParseMode.HTML,
            )
            return

        event_name = " ".join(context.args)
        safe_event_name = html.escape(event_name)
        msg = await update.effective_message.reply_text(
            f"<b>Creating folder for {safe_event_name}...</b>",
            parse_mode=ParseMode.HTML,
        )

        context.application.create_task(
            _create_event_task(update.effective_chat.id, event_name, context.application, msg.message_id)
        )
    except Exception as e:
        log.exception("Unhandled error in create_cmd")
        if update.effective_message:
            await update.effective_message.reply_text(
                f"❌ <b>Critical Error:</b> {html.escape(str(e))}",
                parse_mode=ParseMode.HTML,
            )


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reports uncaught application-level errors back to Telegram.

    Args:
        update: Telegram update object or other context payload.
        context: Telegram callback context.

    Returns:
        None
    """
    log.exception("Unhandled bot error", exc_info=context.error)

    if isinstance(update, Update) and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ <b>Critical Error:</b> {html.escape(str(context.error))}",
            parse_mode=ParseMode.HTML,
        )


def build_application() -> Application:
    """Builds and configures the Telegram application.

    Returns:
        Application: Configured Telegram app with handlers.

    Raises:
        RuntimeError: If the TELEGRAM_TOKEN environment variable is missing.
    """
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN is missing in the .env file.")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("create", create_cmd))
    app.add_error_handler(global_error_handler)
    return app


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("bot.log", encoding="utf-8"),
        ],
    )
    app = build_application()
    keep_alive()
    log.info("Bot is starting up in POLLING mode...")
    app.run_polling()
