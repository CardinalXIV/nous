from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from pymongo import MongoClient
from dotenv import load_dotenv
from fuzzywuzzy import fuzz
from datetime import datetime
from transformers import pipeline
import os, dateparser, logging, spacy, re

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load the text classification model from Hugging Face with TensorFlow backend
classifier = pipeline("text-classification", model="distilbert-base-uncased-finetuned-sst-2-english", framework="tf")

# Load environment variables from .env file
load_dotenv()

# Access the variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
MONGO_URI = os.getenv('MONGODB_URI')

# Set up MongoDB connection
client = MongoClient(MONGO_URI)
db = client['TechnitosNousBotDB']
reminders_collection = db['reminders']

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
    logger.debug("spaCy model loaded successfully.")
except Exception as e:
    logger.error(f"Error loading spaCy model: {e}")
    nlp = None

def recognize_intent(user_message):
    user_message = user_message.lower()
    doc = nlp(user_message)
    
    if "remind" in user_message or "reminder" in user_message:
        if "delete" in user_message or "remove" in user_message:
            return "delete_reminder"
        if "list" in user_message or "show" in user_message or "what" in user_message:
            return "list_reminders"
        if "clear all" in user_message or "clear" in user_message:
            return "clear_reminders"
        return "reminder"
    
    if "hello" in user_message or "hi" in user_message or "hey" in user_message:
        return "greeting"
    
    return "fallback"

import re
from datetime import datetime

def clean_reminder_text(user_message, parsed_date):
    if isinstance(parsed_date, datetime):
        date_str = parsed_date.strftime('%Y-%m-%d %H:%M:%S')
    else:
        date_str = parsed_date  # Use the string as-is if not a datetime object

    # Remove the specific time and date phrases while preserving the rest of the message
    cleaned_message = re.sub(r'\bat\b\s*\b(\d{1,2}[:.]\d{2}\s*(AM|PM)?|\d{1,2}\s*(AM|PM)|morning|afternoon|evening|night)\b', '', user_message, flags=re.IGNORECASE)
    cleaned_message = re.sub(r'\btomorrow\b', '', cleaned_message, flags=re.IGNORECASE)
    cleaned_message = re.sub(r'\btoday\b', '', cleaned_message, flags=re.IGNORECASE)
    cleaned_message = re.sub(r'\bon\b\s*\b(\d{1,2}/\d{1,2}/\d{2,4})\b', '', cleaned_message, flags=re.IGNORECASE)
    cleaned_message = cleaned_message.strip()

    # Clean up multiple spaces resulting from text removal
    cleaned_message = re.sub(r'\s+', ' ', cleaned_message)

    # Return the cleaned up reminder text along with the date
    if 'remind' in cleaned_message:
        cleaned_message = cleaned_message.replace('remind', '').strip()
        return f"Reminder: {cleaned_message} at {date_str}"
    return f"Reminder: {cleaned_message} at {date_str}"


def extract_datetime(user_message):
    # Try to parse the datetime from the message using dateparser
    parsed_date = dateparser.parse(user_message, settings={'PREFER_DATES_FROM': 'future'})
    logger.debug(f"Parsed date using dateparser: {parsed_date}")

    if parsed_date:
        return parsed_date

    # If dateparser fails, try using spaCy to extract date/time entities
    if nlp is not None:
        doc = nlp(user_message)
        for ent in doc.ents:
            if ent.label_ in ["TIME", "DATE"]:
                logger.debug(f"Extracted date using spaCy: {ent.text}")
                # Try to convert spaCy's extracted date into a datetime object
                try:
                    return datetime.strptime(ent.text, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return ent.text  # Keep as string if parsing fails
    
    return None

async def handle_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.strip()
    parsed_date = extract_datetime(user_message)

    if parsed_date:
        cleaned_reminder = clean_reminder_text(user_message, parsed_date)
        
        # Format the date string properly if parsed_date is a datetime object
        date_str = parsed_date if isinstance(parsed_date, str) else parsed_date.strftime('%Y-%m-%d %H:%M:%S')
        
        reminder_doc = {
            "user_id": update.message.from_user.id,
            "reminder": cleaned_reminder,
            "date": date_str
        }
        
        result = reminders_collection.insert_one(reminder_doc)
        logger.debug(f"Reminder saved to database with id: {result.inserted_id}")
        await update.message.reply_text(f"{cleaned_reminder}")
    else:
        await update.message.reply_text("I couldn't recognize the date or time in your reminder. Could you please specify when you want to be reminded?")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    intent = recognize_intent(user_message)
    logger.debug(f"User message: {user_message}")
    logger.debug(f"Recognized intent: {intent}")
    
    if intent == "greeting":
        await update.message.reply_text("Hello! How can I help you today? You can set a reminder or ask me a question.")
    elif intent == "reminder":
        await handle_reminder(update, context)
    elif intent == "list_reminders":
        await list_reminders(update, context)
    elif intent == "clear_reminders":
        await clear_reminders(update, context)
    elif intent == "delete_reminder":
        await delete_reminder(update, context)
    else:
        await update.message.reply_text("I'm not sure what you mean. Could you clarify?")

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    reminders = list(reminders_collection.find({"user_id": user_id}))

    if reminders:
        response = "Here are your reminders:\n"
        for reminder in reminders:
            display_date = reminder['date'] if isinstance(reminder['date'], str) else reminder['date'].strftime('%Y-%m-%d %H:%M:%S')
            response += f"- {reminder['reminder']} on {display_date}\n"
        logger.debug(f"Retrieved reminders for user {user_id}: {reminders}")
        await update.message.reply_text(response)
    else:
        await update.message.reply_text("You have no reminders set.")

async def clear_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    result = reminders_collection.delete_many({"user_id": user_id})
    
    if result.deleted_count > 0:
        logger.debug(f"Cleared {result.deleted_count} reminders for user {user_id}")
        await update.message.reply_text(f"All your reminders have been cleared.")
    else:
        await update.message.reply_text("You have no reminders to clear.")

async def delete_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.lower()
    user_id = update.message.from_user.id
    
    reminders = list(reminders_collection.find({"user_id": user_id}))
    if reminders:
        best_match = None
        best_score = 0
        for reminder in reminders:
            score = fuzz.partial_ratio(user_message, reminder['reminder'].lower())
            if score > best_score:
                best_score = score
                best_match = reminder

        if best_match and best_score > 70:  # Adjust the threshold as needed
            reminders_collection.delete_one({"_id": best_match["_id"]})
            await update.message.reply_text(f"Deleted reminder: {best_match['reminder']}")
        else:
            await update.message.reply_text("I couldn't find a matching reminder to delete. Could you try specifying it more clearly?")
    else:
        await update.message.reply_text("You have no reminders to delete.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == '__main__':
    main()
