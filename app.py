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

# Configuration - use environment variables or default to provided values
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7891364700:AAEryaDwoFsNw60DDJufT9bTfb2Qv0hLyD0")
CHANNEL_ID = os.environ.get("CHANNEL_ID")  # No default, must be set in environment
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "your_secret_key_here")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "smxflixbot")
WEBSITE_URL = os.environ.get("WEBSITE_URL", "https://smxflix.netlify.app")

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
            f"Welcome to SMXFlix Bot! I can send you videos from our collection.\n\n"
            f"Visit {WEBSITE_URL} to browse available videos."
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        f"Visit {WEBSITE_URL} to browse and download videos.\n"
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
            text=f"Sorry, I couldn't find that video (ID: {video_id}). Please try again later.\n\n"
                 f"Go back to {WEBSITE_URL} to try another video."
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
    return f"""
    <html>
        <head>
            <title>SMXFlix Bot</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    text-align: center;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                }}
                h1 {{
                    color: #333;
                }}
                .btn {{
                    display: inline-block;
                    background-color: #0088cc;
                    color: white;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>SMXFlix Bot is running!</h1>
                <p>This is the backend service for the SMXFlix Telegram bot.</p>
                <p>Visit our website to browse videos:</p>
                <a href="{WEBSITE_URL}" class="btn">Go to SMXFlix</a>
                <p>Or chat with our bot directly:</p>
                <a href="https://t.me/{BOT_USERNAME}" class="btn">Open Bot</a>
            </div>
        </body>
    </html>
    """

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
            f"Thanks for sharing your contact. Visit {WEBSITE_URL} to browse videos."
        )

# Special route to handle direct video requests (useful for testing)
@app.route('/direct-video/<video_id>/<user_id>')
def direct_video(video_id, user_id):
    return f"""
    <html>
        <head>
            <title>SMXFlix Video Request</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    text-align: center;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                }}
                h1 {{
                    color: #333;
                }}
                .btn {{
                    display: inline-block;
                    background-color: #0088cc;
                    color: white;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Your video is ready!</h1>
                <p>Click the button below to receive your video on Telegram:</p>
                <a href="/request-video/{video_id}/{user_id}?secret={WEBHOOK_SECRET}" class="btn">Get Video</a>
            </div>
        </body>
    </html>
    """

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