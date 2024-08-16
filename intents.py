import spacy
from transformers import pipeline
from logging_config import logger

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
    logger.debug("spaCy model loaded successfully.")
except Exception as e:
    logger.error(f"Error loading spaCy model: {e}")
    nlp = None

# Load the text classification model from Hugging Face with TensorFlow backend
classifier = pipeline("text-classification", model="distilbert-base-uncased-finetuned-sst-2-english", framework="tf")

def recognize_intent(user_message):
    user_message = user_message.lower()
    doc = nlp(user_message)
    
    # First, let's classify the message
    classification = classifier(user_message)[0]
    
    # Recognize query intent based on keywords
    if any(keyword in user_message for keyword in ["what", "how", "who", "where", "when", "why"]):
        return "query"

    # Recognize reminder intent based on keywords
    if "remind" in user_message or "reminder" in user_message:
        if "delete" in user_message or "remove" in user_message:
            return "delete_reminder"
        if "list" in user_message or "show" in user_message:
            return "list_reminders"
        if "clear all" in user_message or "clear" in user_message:
            return "clear_reminders"
        return "reminder"
    
    if "hello" in user_message or "hi" in user_message or "hey" in user_message:
        return "greeting"
    
    return "fallback"
