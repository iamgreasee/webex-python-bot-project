import json
from flask import Flask, request
from dotenv import load_dotenv
import os
import random
from common.utils import create_webhook
from webexpythonsdk import WebexAPI, Webhook

# Load environment variables from .env file
load_dotenv()

# Get the bot access token from the environment variable
WEBEX_TEAMS_ACCESS_TOKEN = os.getenv('WEBEX_TEAMS_ACCESS_TOKEN')

if not WEBEX_TEAMS_ACCESS_TOKEN:
    raise ValueError("WEBEX_TEAMS_ACCESS_TOKEN is not set correctly in the environment variables")

teams_api = WebexAPI(access_token=WEBEX_TEAMS_ACCESS_TOKEN)
active_games = {}

# Dictionary of flags and countries
flags = {
    "Israel": "🇮🇱",
    "United States": "🇺🇸",
    "Canada": "🇨🇦",
    "Germany": "🇩🇪",
    "Japan": "🇯🇵",
    "Brazil": "🇧🇷",
    "India": "🇮🇳",
    "France": "🇫🇷",
    "Mexico": "🇲🇽",
    "Italy": "🇮🇹"
}

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
        commands_split = (message.split())[1:]
        command = ' '.join(commands_split)
        parse_message(command, data.personEmail, data.roomId)
        return '200'

def parse_message(command, sender, roomId):
    if command == "start game":
        if roomId not in active_games:
            start_game(roomId, sender)
    elif command.startswith("guess"):
        guess = command.split(" ", 1)[1]
        if roomId in active_games:
            check_guess(roomId, guess, sender)
    elif command == "scoreboard":
        if roomId in active_games:
            show_scoreboard(roomId)
    elif command == "stop game":
        stop_game(roomId)
    elif command == "help":
        send_message_in_room(roomId, help_text())
    return

def help_text():
    return (
        "Here are the available commands:\n"
        "- **start game**: Start a new flag guessing game.\n"
        "- **guess <country_name>**: Guess which country the flag represents.\n"
        "- **scoreboard**: Show the current scoreboard.\n"
        "- **stop game**: End the game.\n"
        "- **help**: Display this list of commands."
    )

def generate_flag_card(roomId, flag_emoji):
    return {
        "contentType": "application/vnd.microsoft.card.adaptive",
        "content": {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.1",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Guess which country this flag represents:",
                    "size": "large"
                },
                {
                    "type": "TextBlock",
                    "text": flag_emoji,
                    "size": "medium"
                },
                {
                    "type": "TextBlock",
                    "text": "Type your guess using the 'guess <country_name>' command.",
                    "weight": "bolder"
                }
            ],
            "actions": []
        }
    }

def generate_scoreboard_card(roomId, scoreboard):
    card_results = {
        "contentType": "application/vnd.microsoft.card.adaptive",
        "content": {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.1",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Current Scoreboard:",
                    "size": "large"
                }
            ],
            "actions": []
        }
    }
    for player, score in scoreboard.items():
        card_results["content"]["body"].append({
            "type": "TextBlock",
            "text": f"{player}: *{score}*"
        })
    return card_results

def start_game(roomId, sender):
    # Randomly select a flag and country
    country, flag_emoji = random.choice(list(flags.items()))
    
    active_games[roomId] = {
        'flag_emoji': flag_emoji,
        'correct_answer': country,
        'players': {sender: 0}
    }
    teams_api.messages.create(roomId=roomId, text="Game Started!", attachments=[generate_flag_card(roomId, flag_emoji)])

def check_guess(roomId, guess, sender):
    game = active_games[roomId]
    
    if guess.lower() == game['correct_answer'].lower():
        # Correct guess
        if sender not in game['players']:
            game['players'][sender] = 0  # Initialize score for a new player if not present
        game['players'][sender] += 1  # Increment score by 1
        send_message_in_room(roomId, f"Correct, {sender}! Your score has been updated.")
        
        # After correct guess, show a new flag (but preserve score)
        country, flag_emoji = random.choice(list(flags.items()))
        game['flag_emoji'] = flag_emoji
        game['correct_answer'] = country
        
        teams_api.messages.create(roomId=roomId, text="New Flag! Guess again!", attachments=[generate_flag_card(roomId, flag_emoji)])
    else:
        send_message_in_room(roomId, f"Wrong guess, {sender}. Try again!")


def show_scoreboard(roomId):
    game = active_games[roomId]
    send_message_in_room(roomId, "Here is the current scoreboard:", attachments=[generate_scoreboard_card(roomId, game['players'])])

def stop_game(roomId):
    if roomId in active_games:
        del active_games[roomId]
        send_message_in_room(roomId, "Game has been stopped. Thanks for playing!")
    else:
        send_message_in_room(roomId, "No game is currently running.")

def send_message_in_room(room_id, message, attachments=None):
    teams_api.messages.create(roomId=room_id, text=message, attachments=attachments)



@app.route('/attachmentActions_webhook', methods=['POST'])
def attachmentActions_webhook():
    if request.method == 'POST':
        print("attachmentActions POST!")
        webhook_obj = Webhook(request.json)
        return process_card_response(webhook_obj.data)

def process_card_response(data):
    attachment = teams_api.attachment_actions.get(data.id).json_data
    inputs = attachment['inputs']
    return '200'

@app.route('/test', methods=['GET'])
def test():
    return "Test endpoint is working."

if __name__ == '__main__':
    teams_api = WebexAPI(access_token=WEBEX_TEAMS_ACCESS_TOKEN)
    create_webhook(teams_api, 'messages_webhook', '/messages_webhook', 'messages')
    create_webhook(teams_api, 'attachmentActions_webhook', '/attachmentActions_webhook', 'attachmentActions')
    app.run(host='0.0.0.0', port=12000)

