import os
import time
from slackclient import SlackClient
import wizardgame as WizardGame
from collections import defaultdict

# wizardbot's ID as an environment variable
BOT_ID = os.environ.get("BOT_ID")

# constants
AT_BOT = "<@" + BOT_ID + ">"

# instantiate Slack & Twilio clients
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
users_in_game = []
user_id_to_username = {}
channel_ids_to_name = {}
private_message_channel_ids_to_username = {}
main_channel_id = 'C2F154UTE'

def handle_command(command, channel, user_id):
    #TODO restrict the channel this is in
    username = user_id_to_username[user_id] #user who sent the message
    response = "Hey! So uh...this is awkward, but I only respond to game commands." #default response

    if command.lower().startswith("create game"):
        if len(users_in_game) == 0:
            response = "<@{}> Wants to play a game of wizard! Tell me `add me` to play.".format(username)
            users_in_game.append(user_id)
        else:
            response = "There's already a game being made, say `add me` if you want in."

    if command.lower().startswith("cancel"):
        response = "Okay, game cancelled."
        while len(users_in_game) > 0:
            users_in_game.pop()

    if command.lower().startswith("add me"):
        if len(users_in_game) == 0:
            response = "There is no active game, try `create game`."
        else:
            if user_id in users_in_game:
                response = "You've already been added to the game."
            else:
                users_in_game.append(user_id)
                response = "Added <@{}> to the game!".format(username)

    if command.lower().startswith("start game"):
        if len(users_in_game) == 0:
            response = "No game exists yet. Try `create game`"
         #TODO this should be minimum for 3 players.
         #TODO is there a max number of players?
        elif len(users_in_game) < 2:
            response = "There aren't enough players yet (minimum 4). Users can say `add me` to be added to the game."
        else:
            response = "Starting a new game of Wizard with players: \n" + get_readable_list_of_players()
            play_game_of_wizard_on_slack(users_in_game, channel)

    slack_client.api_call("chat.postMessage", channel=channel,
                          text=response, as_user=True)

def handle_private_message(command, user_id, is_asking_for_bid=False, is_asking_for_card_to_play=False):
    slack_client.api_call(
        "chat.postMessage",
        channel=user_id,
        text=command,
        as_user=True
    )

def get_bids_from_players(player_objects, current_round):
    #ask, in order, for each players' bid
    player_bids = defaultdict(list)
    for player in player_objects:
        slack_client.api_call(
            "chat.postMessage",
            channel=player.id,
            text="What's your bid for the round?",
            as_user=True
        )
        while len(player_bids[player.id]) == 0:
            pass


def prompt_dealer_for_trump_suit(player_id):
    slack_client.api_call(
        "chat.postMessage",
        channel=player_id,
        text="please select index for trump suit \n [:diamonds:][:clubs:][:hearts:][:spades:]",
        as_user=True
    )

def get_readable_list_of_players():
    #TODO refactor this with less mumbojumbo
    player_names = []
    printable_player_names = []
    for player_id in users_in_game:
        player_names.append(user_id_to_username[player_id])
    for idx, player_name in enumerate(player_names):
        printable_player_names.append("{}) <@{}>".format(idx + 1, player_name))
    return (' \n ').join(printable_player_names)

def display_cards_for_player_in_pm(player_id, cards):
    formatted_cards = format_cards_to_emojis(cards)
    slack_client.api_call(
        "chat.postMessage",
        channel=player_id,
        text="Your card(s): {} \n What's your bid?".format(formatted_cards),
        as_user=True
    )

def announce_trump_suit(trump_card):
    slack_client.api_call(
        "chat.postMessage",
        channel=main_channel_id,
        text="*Round 1* \n The trump card is: [{}:{}:]".format(trump_card[0], trump_card[1]
        ),
        as_user=True
    )

def format_cards_to_emojis(cards):
    formatted_cards = []
    for card in cards:
        if len(card) == 2:
            formatted_cards.append("[{}:{}:]".format(card[0],card[1]))
        else:
            formatted_cards.append(":{}:").format(card)
    return "".join(formatted_cards)

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

#takes an array of player_ids and the channel the game request originated from
def play_game_of_wizard_on_slack(players, channel):
    player_objects = []
    for player_id in players:
        player_objects.append(WizardGame.Player(player_id))

    game = WizardGame.Game(player_objects)
    game.play_round()

if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose

    #grab user list and converts it to to a dict of ids to usernames
    api_call = slack_client.api_call("users.list")

    if api_call.get('ok'):
        users = api_call.get('members')
        for user in users:
            user_id_to_username[user['id']] = user['name']

    channels = slack_client.api_call("channels.list").get('channels')
    for channel in channels:
        channel_ids_to_name[channel['id']] = channel['name']


    if slack_client.rtm_connect():
        print("WizardBot connected and running!")

        while True:
            command, channel, user = parse_slack_output(slack_client.rtm_read())
            if command and channel:
                if channel not in channel_ids_to_name.keys():
                    #this (most likely) means that this channel is a PM with the bot
                    handle_private_message(command, user)
                else:
                    handle_command(command, channel, user)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Invalid Slack token or bot ID?")
