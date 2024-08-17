import re, dateparser
from datetime import datetime
from logging_config import logger
from intents import nlp

import re
from datetime import datetime

def clean_reminder_text(user_message, parsed_date, nlp):
    if isinstance(parsed_date, datetime):
        date_str = parsed_date.strftime('%Y-%m-%d %H:%M:%S')
    else:
        date_str = parsed_date

    # Define a list of phrases and patterns to remove
    phrases_to_remove = [
        r'\b(at\s*)?\d{1,2}[:.]\d{2}\s*(am|pm)?',
        r'\b(at\s*)?\d{1,2}\s*(am|pm)',
        r'\b\d{1,2}[:.]\d{2}\s*(am|pm)?|\d{1,2}\s*(am|pm)',
        r'\b(morning|afternoon|evening|night|tomorrow|today)\b',
        r'\bon\s*\b\d{1,2}/\d{1,2}/\d{2,4}\b',
        r'\bon\s*\b\d{1,2}/\d{1,2}/\d{2,4}\b'
    ]

    # Remove the unnecessary parts from the user message
    cleaned_message = user_message
    for phrase in phrases_to_remove:
        cleaned_message = re.sub(phrase, '', cleaned_message, flags=re.IGNORECASE)

    # Further refinement using dependency parsing
    doc = nlp(cleaned_message)
    relevant_tokens = []
    for token in doc:
        if token.dep_ not in ("punct", "cc", "det", "aux", "mark"):  # Ignore less important parts of speech
            relevant_tokens.append(token.text)

    cleaned_message = " ".join(relevant_tokens).strip()

    # Ensure the final text is concise and accurate
    if not cleaned_message:  # Avoid returning an empty string
        cleaned_message = user_message.strip()

    return f"{cleaned_message} on {date_str}"


def extract_datetime(user_message, nlp):
    # Try to parse the datetime from the message using dateparser
    parsed_date = dateparser.parse(user_message, settings={'PREFER_DATES_FROM': 'future'})
    logger.debug(f"Parsed date using dateparser: {parsed_date}")

    if parsed_date:
        return parsed_date

    # Use spaCy to extract date/time entities
    if nlp is not None:
        doc = nlp(user_message)
        for ent in doc.ents:
            if ent.label_ in ["TIME", "DATE"]:
                logger.debug(f"Extracted date using spaCy: {ent.text}")
                try:
                    # Attempt to parse this as a datetime
                    return dateparser.parse(ent.text)
                except ValueError:
                    return ent.text  # Keep as string if parsing fails
    
    return None

