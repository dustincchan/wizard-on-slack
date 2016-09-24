import os
import time
from slackclient import SlackClient
import wizardgame

# wizardbot's ID as an environment variable
BOT_ID = os.environ.get("BOT_ID")

# constants
AT_BOT = "<@" + BOT_ID + ">"

# instantiate Slack & Twilio clients
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
users_in_game = []
user_id_to_username = {}

def handle_command(command, channel, user_id):
    username = user_id_to_username[user_id] #user who sent the message
    response = "I'm not sure what you meant by that." #default response

    if command.lower().startswith("create game"):
        if len(users_in_game) == 0:
            response = "<@{}> Wants to play a game of wizard! Tell me _'add me'_ to play.".format(username)
            users_in_game.append(user_id)
        else:
            response = "There is already a game being initialized, say _'add me' if you want in."

    if command.lower().startswith("cancel"):
        response = "Okay, game cancelled."
        users_in_game = []

    if command.lower().startswith("add me"):
        if len(users_in_game) == 0:
            response = "There is no active game, try _'create game'_."
        else:
            if user_id in users_in_game:
                response = "You've already been added to the game."
            else:
                users_in_game.append(user_id)
                response = "Added <@{}> to the game!".format(username)

    if command.lower().startswith("start game"):
        response = "Starting a new game of Wizard with players: \n" + get_readable_list_of_players()
        play_game_of_wizard(users_in_game)

    slack_client.api_call("chat.postMessage", channel=channel,
                          text=response, as_user=True)

def get_readable_list_of_players():
    #TODO refactor this with less mumbojumbo
    player_names = []
    printable_player_names = []
    for player_id in users_in_game:
        player_names.append(user_id_to_username[player_id])
    for idx, player_name in enumerate(player_names):
        printable_player_names.append("{}) <@{}>".format(idx + 1, player_name))
    return (' \n ').join(printable_player_names)

def parse_slack_output(slack_rtm_output):
    """
        The Slack Real Time Messaging API is an events firehose.
        this parsing function returns None unless a message is
        directed at the Bot, based on its ID.
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and AT_BOT in output['text']:
                # return text after the @ mention, whitespace removed

                #example return: (u'hi', u'C2F154UTE', )
                return output['text'].split(AT_BOT)[1].strip().lower(), \
                       output['channel'], output['user']
    return None, None, None


def play_game_of_wizard(players):
    pass

if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose

    #grab user list and converts it to to a dict of ids to usernames
    api_call = slack_client.api_call("users.list")
    if api_call.get('ok'):
        users = api_call.get('members')
        for user in users:
            user_id_to_username[user['id']] = user['name']


    if slack_client.rtm_connect():
        print("WizardBot connected and running!")
        while True:
            command, channel, user = parse_slack_output(slack_client.rtm_read())
            if command and channel:
                handle_command(command, channel, user)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Invalid Slack token or bot ID?")
