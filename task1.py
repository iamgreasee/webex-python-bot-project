from ctypes import util
from flask import Flask, request
from dotenv import load_dotenv
import os

from common.utils import create_webhook
from webexpythonsdk import WebexAPI, Webhook

# Load environment variables from .env file
load_dotenv()

# Get the bot access token from the environment variable
load_dotenv()
WEBEX_TEAMS_ACCESS_TOKEN = os.getenv('WEBEX_TEAMS_ACCESS_TOKEN')
print(WEBEX_TEAMS_ACCESS_TOKEN)  # This will help confirm the token is correctly loaded.

if not WEBEX_TEAMS_ACCESS_TOKEN:
    raise ValueError("WEBEX_TEAMS_ACCESS_TOKEN is not set correctly in the environment variables")

teams_api = None

app = Flask(__name__)
@app.route('/messages_webhook', methods=['POST'])
def messages_webhook():
    if request.method == 'POST':
        webhook_obj = Webhook(request.json)
        return process_message(webhook_obj.data)

def process_message(data):
    if data.personId == teams_api.people.me().id:
        # Message sent by bot, do not respond
        return '200'
    else:
        message = teams_api.messages.get(data.id).text
        print(message)
        send_message_in_room(data.roomId, f"Hello {data.personEmail}!")
        return '200'

def send_direct_message(person_email, message):
    teams_api.messages.create(toPersonEmail=person_email, text=message)

def send_message_in_room(room_id, message):
    teams_api.messages.create(roomId=room_id, text=message)

if __name__ == '__main__':
    teams_api = WebexAPI(access_token=WEBEX_TEAMS_ACCESS_TOKEN)
    create_webhook(teams_api, 'messages_webhook', '/messages_webhook', 'messages')
    app.run(host='0.0.0.0', port=12000)

