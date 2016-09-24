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

def handle_command(command, channel, user_id): #user is user_id
    print(user)
    response = "Not sure what you mean. If you want to start a game, then tell me _'add me'_"

    if command.lower().startswith("add me"):
        if len(users_in_game) == 0:
            response = "{} Wants to play a game of wizard! Message me to play".format(user_id)
            users_in_game.append(user_id)
        else:
            users_in_game.append(user_id)
            response = "Added {} to the game!".format(user_id)
            print(users_in_game)

    slack_client.api_call("chat.postMessage", channel=channel,
                          text=response, as_user=True)

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
