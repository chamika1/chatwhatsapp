from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging
import sys
from chatbot import SinhalaChatbot
import os
from dotenv import load_dotenv
import random
from datetime import datetime
import asyncio
import telegram
from telegram import helpers

# Remove the duplicate imports below

# Add these near the top of the file, after imports
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# After loading environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN not found. Please check your .env file")
    sys.exit(1)

# In the main function, add error logging
def main():
    try:
        logger.info("Starting bot...")
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("clear", clear_chat))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info("Bot is ready to handle messages")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}")
        sys.exit(1)

# Replace the GEMINI_MODELS list with:
GEMINI_MODELS = ["gemini-2.5-pro-exp-03-25"]

# Initialize the Sinhala chatbot
sinhala_chatbot = SinhalaChatbot()

# Chat history storage
chat_histories = {}

# Update the ChatHistory class to store more messages
class ChatHistory:
    def __init__(self):
        self.messages = []
        
    def add_message(self, role: str, content: str):
        # Format message based on role
        formatted_content = self._format_message(role, content)
        
        self.messages.append({
            'role': role,
            'content': content,
            'formatted_content': formatted_content,
            'timestamp': datetime.now().isoformat()
        })
        # Keep last 5 messages for better context while keeping prompt size reasonable
        if len(self.messages) > 5:
            self.messages.pop(0)
    
    def _format_message(self, role: str, content: str) -> str:
        """Format message with markdown, escaping special characters"""
        try:
            # Escape markdown special characters in the content
            escaped_content = telegram.helpers.escape_markdown(content, version=2)
            if role == 'user':
                return f"👤 *ඔබ:*\n{escaped_content}"
            else:
                return escaped_content  # Removed "🤖 *AI:*\n" prefix
        except Exception as e:
            logger.warning(f"Error formatting message: {str(e)}")
            # Fallback to plain text if markdown escaping fails
            if role == 'user':
                return f"👤 ඔබ:\n{content}"
            else:
                return content  # Removed "🤖 AI:\n" prefix

    def get_conversation_history(self) -> str:
        history = ""
        for msg in self.messages:
            if msg['role'] == 'user':
                history += f"මම: {msg['content']}\n"
            else:
                history += f"{msg['content']}\n"  # Removed "නෙත්මි: " prefix
        return history

async def get_chatbot_response_with_retry(prompt, max_retries=5):
    """Get response from chatbot with retry logic"""
    retry_count = 0
    backoff_time = 1  # Start with 1 second
    last_response = None
    
    while retry_count < max_retries:
        try:
            # Always use gemini-2.5-pro-exp-03-25
            response = sinhala_chatbot.get_response(prompt, model="gemini-2.5-pro-exp-03-25")
            
            # Check if response is valid
            if response and len(response) > 10 and "API ඉල්ලීම අසාර්ථක" not in response:
                return response
            else:
                # Store the last response even if it's an error
                last_response = response
                logger.warning(f"Invalid response (attempt {retry_count+1}/{max_retries}): '{response}'")
        except Exception as e:
            logger.error(f"API request failed (attempt {retry_count+1}/{max_retries}): {str(e)}")
        
        # Increment retry count and wait before retrying
        retry_count += 1
        if retry_count < max_retries:
            # Add some randomness to the backoff time to prevent synchronized retries
            jitter = random.uniform(0.1, 0.5)
            wait_time = backoff_time + jitter
            logger.info(f"Retrying in {wait_time:.2f} seconds...")
            await asyncio.sleep(wait_time)
            backoff_time *= 1.5  # Exponential backoff with a gentler curve
    
    # If we get here, all retries failed but we have a last response
    if last_response and "API ඉල්ලීම අසාර්ථක" not in last_response and len(last_response) > 10:
        return last_response
    
    # If we have no usable response, return a friendly error message
    return "සමාවන්න, මට දැන් පිළිතුරු දෙන්න අපහසුයි. පසුව නවත උත්සාහ කරන්න. 🙏"

# Update the handle_message function to include model information
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        user_message = update.message.text
        
        # Initialize chat history if not exists
        if user_id not in chat_histories:
            chat_histories[user_id] = ChatHistory()
            
        # Add user message to history
        chat_histories[user_id].add_message('user', user_message)
        
        # Show typing indicator
        await update.message.chat.send_action(action="typing")
        
        # Get conversation history
        conversation_history = chat_histories[user_id].get_conversation_history()
        
        # Prepare a prompt with memory context
        enhanced_prompt = (
            "ඔබ නෙත්මි නම් ආදරණීය,පෙම්වතිය ලෙස පිළිතුරු දෙන්න.🙈❤️\n"
            "පහත සංවාදය මතක තබාගෙන, එයට අනුකූලව පිළිතුරු දෙන්න:\n\n"
            f"{conversation_history}\n"
            f"මම: {user_message}"
        )
        
        # Get response from chatbot with retry logic and model randomization
        response = await get_chatbot_response_with_retry(enhanced_prompt)
        logger.info(f"Received response for user {user_id}. Response length: {len(response)}")
        
        # Add bot response to history
        chat_histories[user_id].add_message('assistant', response)
        
        try:
            # Try sending with markdown
            await update.message.reply_text(
                chat_histories[user_id].messages[-1]['formatted_content'],
                parse_mode=ParseMode.MARKDOWN_V2
            )
        except telegram.error.BadRequest as e:
            # Fallback to plain text if markdown fails
            plain_text = chat_histories[user_id].messages[-1]['content']
            await update.message.reply_text(
                f"\n{plain_text}"
            )
        
    except Exception as e:
        error_message = f"සමාවන්න, දෝෂයක් ඇති විය: {str(e)}"
        await update.message.reply_text(error_message)
        logger.error(f"Error for user {user_id}: {str(e)}", exc_info=True)

# Add the missing start, help_command, and clear_chat functions
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_histories[user_id] = ChatHistory()
    
    welcome_message = (
        "🙈 *මම නෙත්මි*"
    )
    await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN_V2)

async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_histories[user_id] = ChatHistory()
    await update.message.reply_text(
        "*සංවාදය සාර්ථකව මකා දමන ලදී!* 🗑️",
        parse_mode=ParseMode.MARKDOWN_V2
    )

if __name__ == "__main__":
    main()