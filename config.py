import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_PATH = os.getenv('DATABASE_PATH', 'bot_database.db')
CLIENT_ID = os.getenv('CLIENT_ID')
PUBLIC_KEY = os.getenv('PUBLIC_KEY')
INTERACTION_ENDPOINT_PORT = int(os.getenv('INTERACTION_ENDPOINT_PORT', '8000'))
