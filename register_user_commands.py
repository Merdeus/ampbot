import requests
import json
from config import CLIENT_ID, DISCORD_TOKEN

def register_user_commands():
    if not CLIENT_ID or not DISCORD_TOKEN:
        print("Error: CLIENT_ID and DISCORD_TOKEN must be set in .env")
        return
    
    url = f"https://discord.com/api/v10/applications/{CLIENT_ID}/commands"
    
    headers = {
        "Authorization": f"Bot {DISCORD_TOKEN}",
        "Content-Type": "application/json"
    }
    
    commands = [
        {
            "name": "history",
            "description": "View bot history, optionally filtered by user",
            "options": [
                {
                    "name": "user",
                    "description": "Filter history by a specific user",
                    "type": 6,
                    "required": False
                },
                {
                    "name": "limit",
                    "description": "Number of entries to show (1-100)",
                    "type": 4,
                    "required": False,
                    "min_value": 1,
                    "max_value": 100
                }
            ]
        }
    ]
    
    for command in commands:
        response = requests.post(url, headers=headers, json=command)
        if response.status_code == 200 or response.status_code == 201:
            print(f"✓ Registered command: {command['name']}")
        else:
            print(f"✗ Failed to register {command['name']}: {response.status_code} - {response.text}")

if __name__ == '__main__':
    register_user_commands()

