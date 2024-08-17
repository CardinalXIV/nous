from telegram import Update
from telegram.ext import ContextTypes
from reminder import Reminder
from config import reminders_collection
from intents import recognize_intent, nlp
from fuzzywuzzy import fuzz
from logging_config import logger
from datetime import datetime

async def handle_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.strip()
    reminder = Reminder(update.message.from_user.id, user_message, nlp)

    if reminder.parsed_date:
        try:
            reminder_doc = {
                "user_id": reminder.user_id,
                "reminder": reminder.cleaned_message,
                "date": reminder.parsed_date.strftime('%Y-%m-%d %H:%M:%S')
            }
            result = reminders_collection.insert_one(reminder_doc)
            logger.debug(f"Reminder saved to database with id: {result.inserted_id}")
            await update.message.reply_text(reminder.get_reminder_text())
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
            # Check if the date is in the expected datetime format
            try:
                if isinstance(reminder['date'], str):
                    if reminder['date'].lower() in ["tomorrow", "today"]:
                        date_display = reminder['date']  # Keep as is if it's a recognized string
                    else:
                        date = datetime.strptime(reminder['date'], '%Y-%m-%d %H:%M:%S')
                        date_display = date.strftime('%d %b %Y %H:%M')
                else:
                    date_display = reminder['date'].strftime('%d %b %Y %H:%M')
                
                response += f"- {reminder['reminder']} on {date_display}\n"
            except ValueError as e:
                logger.error(f"Error parsing date: {reminder['date']} with error {e}")
                response += f"- {reminder['reminder']} on {reminder['date']}\n"  # Fallback to original text

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
    user_message = update.message.text.lower()

    if "what can you do" in user_message:
        await update.message.reply_text("I can set reminders, list your reminders, delete them, and answer simple questions! Just tell me what you need.")
    elif "how does this work" in user_message:
        await update.message.reply_text("You can ask me to set reminders, and I'll make sure to remind you at the right time. Just say something like 'Remind me to call John at 5 PM'.")
    else:
        await update.message.reply_text("I'm here to help! You can set reminders or ask me any questions.")

