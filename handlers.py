from telegram import Update
from telegram.ext import ContextTypes
from utils import clean_reminder_text, extract_datetime
from config import reminders_collection
from intents import recognize_intent, nlp
from fuzzywuzzy import fuzz
from logging_config import logger

async def handle_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.strip()
    parsed_date = extract_datetime(user_message, nlp)

    if parsed_date:
        cleaned_reminder = clean_reminder_text(user_message, parsed_date, nlp)  # Pass nlp here
        
        # Format the date string properly if parsed_date is a datetime object
        date_str = parsed_date if isinstance(parsed_date, str) else parsed_date.strftime('%Y-%m-%d %H:%M:%S')
        
        reminder_doc = {
            "user_id": update.message.from_user.id,
            "reminder": cleaned_reminder,
            "date": date_str
        }
        
        try:
            result = reminders_collection.insert_one(reminder_doc)
            logger.debug(f"Reminder saved to database with id: {result.inserted_id}")
            await update.message.reply_text(f"{cleaned_reminder}")
        except Exception as e:
            logger.error(f"Error saving reminder to database: {e}")
            await update.message.reply_text("There was an issue saving your reminder. Please try again.")
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
    elif intent == "query":
        await handle_query(update, context)
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

async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    # Depending on your implementation, either fetch from a knowledge base or return a standard response
    response = "I can help with setting reminders or answering queries about specific topics. Please ask me about programming languages, frameworks, or set a reminder!"
    await update.message.reply_text(response)
