import re, dateparser, spacy
from datetime import datetime, timedelta
from spacy import Language
from spacy.matcher import Matcher
from logging_config import logger


class Reminder:
    def __init__(self, user_id: int, message: str, nlp: Language):
        self.user_id = user_id
        self.original_message = message
        # Check if nlp is provided, otherwise load the SpaCy model
        if nlp is None:
            self.nlp = spacy.load("en_core_web_sm")
        else:
            self.nlp = nlp
        self.cleaned_message = ""
        self.parsed_date = None
        self.process_message()

    def process_message(self):
        self.parsed_date = self.extract_datetime(self.original_message)
        self.cleaned_message = self.clean_message(self.original_message)

    def extract_datetime(self, message: str):
        # First, attempt to parse with dateparser
        parsed_date = dateparser.parse(message, settings={'PREFER_DATES_FROM': 'future'})
        
        if parsed_date:
            return parsed_date

        # If dateparser fails, try using spaCy to extract date/time entities
        doc = self.nlp(message)
        for ent in doc.ents:
            if ent.label_ in ["TIME", "DATE"]:
                try:
                    return datetime.strptime(ent.text, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    if ent.text.lower() == "tomorrow":
                        return datetime.now() + timedelta(days=1)
                    elif ent.text.lower() == "today":
                        return datetime.now()
                    return ent.text

        return None

    def clean_message(self, message: str):
        phrases_to_remove = [
            r'\b(at\s*)?\d{1,2}[:.]\d{2}\s*(am|pm)?',
            r'\b(at\s*)?\d{1,2}\s*(am|pm)',
            r'\b\d{1,2}[:.]\d{2}\s*(am|pm)?|\d{1,2}\s*(am|pm)',
            r'\b(morning|afternoon|evening|night|tomorrow|today)\b',
            r'\bon\s*\b\d{1,2}/\d{1,2}/\d{2,4}\b'
        ]

        cleaned_message = message
        for phrase in phrases_to_remove:
            cleaned_message = re.sub(phrase, '', cleaned_message, flags=re.IGNORECASE)

        doc = self.nlp(cleaned_message)
        
        # Rule-based matching
        matcher = Matcher(self.nlp.vocab)
        pattern = [{"POS": "VERB"}, {"POS": "NOUN", "OP": "+"}]
        matcher.add("VERB_NOUN_PATTERN", [pattern])
        matches = matcher(doc)
        
        if matches:
            match_id, start, end = matches[0]
            matched_span = doc[start:end]
            return matched_span.text
        
        # Fallback to POS-based extraction
        relevant_tokens = [token.text for token in doc if token.pos_ in ("VERB", "NOUN", "PROPN", "ADJ")]

        return " ".join(relevant_tokens).strip()

    def get_reminder_text(self):
        # Format the date for display purposes
        if isinstance(self.parsed_date, datetime):
            # Format example: "29 Aug 2024 00:00"
            date_str = self.parsed_date.strftime('%d %b %Y %H:%M')
        else:
            date_str = self.parsed_date  # In case parsed_date is a string

        return f"Reminder set: '{self.cleaned_message}' scheduled for {date_str}"

