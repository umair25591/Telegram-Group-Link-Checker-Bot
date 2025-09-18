import os
from dotenv import load_dotenv
from telethon.sync import TelegramClient

# Load credentials from your .env file
load_dotenv()
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")

# This session name MUST MATCH the one in your bot script
SESSION_NAME = "checker_bot_session"

# This code will log you in and create the .session file
print("Attempting to log in to generate session file...")
with TelegramClient(SESSION_NAME, int(API_ID), API_HASH) as client:
    print("Login successful! Session file created.")
    print("You can now close this and run your main bot script.")
    # The client will automatically disconnect when the 'with' block ends