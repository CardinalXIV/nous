import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables from .env file
load_dotenv()

# Access the variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
MONGO_URI = os.getenv('MONGODB_URI')

# Set up MongoDB connection
client = MongoClient(MONGO_URI)
db = client['TechnitosNousBotDB']
reminders_collection = db['reminders']
