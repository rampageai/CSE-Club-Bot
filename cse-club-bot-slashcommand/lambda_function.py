import json
import requests
import os

def lambda_handler(event, context):
    APP_ID = os.environ['APP_ID']
    GUILD_ID = os.environ['GUILD_ID']
    BOT_TOKEN = os.environ['BOT_TOKEN']

    # 1. Define the API endpoint
    url = f"https://discord.com/api/v10/applications/{APP_ID}/guilds/{GUILD_ID}/commands"

    # 2. Define the JSON body as a Python dictionary from tests
    payload = event

    # 3. Define custom headers (e.g., Authentication)
    headers = {
        "Authorization": f"Bot {BOT_TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    # 4. Make the PUT request
    response = requests.post(url, json=payload, headers=headers)

    print(json.dumps(response.json(), indent=4))

    # TODO implement
    return {
        'statusCode': response.status_code,
        'body': json.dumps(response.json(), indent=4)
    }
