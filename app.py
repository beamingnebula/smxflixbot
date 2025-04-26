import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext
from flask import Flask, request, redirect, render_template
import asyncio
import threading
from dotenv import load_dotenv

# Load environment variables from .env file (locally)
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration - use environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")
BOT_USERNAME = os.environ.get("BOT_USERNAME")

# Flask app for handling webhooks from your website
app = Flask(__name__)

# Store user requests temporarily
video_requests = {}

# Initialize the bot with None value first
bot_app = None

def init_bot():
    """Initialize the Telegram bot in a separate thread"""
    global bot_app
    
    # Create the application
    bot_app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("help", help_command))
    bot_app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    
    # Start the bot
    bot_app.run_polling()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user_id = str(update.message.from_user.id)
    
    if user_id in video_requests:
        # If there's a pending video request for this user, send it
        video_id = video_requests[user_id]
        await send_video(int(user_id), video_id)
        # Remove the request after processing
        del video_requests[user_id]
    else:
        await update.message.reply_text(
            "Welcome! I can send you videos from our collection. "
            "Visit our website to browse available videos."
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "Visit our website to browse and download videos. "
        "When you select a video, you'll be redirected here to receive it."
    )

async def send_video(user_id: int, video_id: str) -> None:
    """Send the requested video to the user."""
    try:
        # Forward the message from the channel to the user
        await bot_app.bot.forward_message(
            chat_id=user_id,
            from_chat_id=CHANNEL_ID,
            message_id=int(video_id)
        )
        logger.info(f"Successfully sent video {video_id} to user {user_id}")
    except Exception as e:
        logger.error(f"Error sending video: {e}")
        await bot_app.bot.send_message(
            chat_id=user_id,
            text=f"Sorry, I couldn't find that video (ID: {video_id}). Please try again later."
        )

# Flask route to handle video requests from your website
@app.route('/request-video/<video_id>/<user_id>', methods=['GET'])
def request_video(video_id, user_id):
    if 'secret' not in request.args or request.args.get('secret') != WEBHOOK_SECRET:
        return "Unauthorized", 401
    
    # Store the request in our dictionary
    video_requests[user_id] = video_id
    
    # Create an event loop for the async task
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # If we're not in a test environment, try to send the video directly
    if bot_app and bot_app.bot:
        try:
            loop.run_until_complete(send_video(int(user_id), video_id))
            # Remove the request after processing
            del video_requests[user_id]
        except Exception as e:
            logger.error(f"Error sending video in direct mode: {e}")
    
    # Redirect user to Telegram
    return redirect(f"https://t.me/{BOT_USERNAME}")

@app.route('/')
def index():
    return "Telegram Video Bot is running!"

# Handler for when users share their contact
async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle when users share their contact info."""
    user_id = str(update.message.from_user.id)
    
    if user_id in video_requests:
        # If there's a pending video request for this user, send it
        video_id = video_requests[user_id]
        await send_video(int(user_id), video_id)
        # Remove the request after processing
        del video_requests[user_id]
    else:
        await update.message.reply_text(
            "Thanks for sharing your contact. Visit our website to browse videos."
        )

if __name__ == "__main__":
    # Start the bot in a separate thread
    threading.Thread(target=init_bot, daemon=True).start()
    
    # Run the Flask app
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
else:
    # If we're being imported (like in a production WSGI environment)
    # Start the bot in a separate thread
    threading.Thread(target=init_bot, daemon=True).start()