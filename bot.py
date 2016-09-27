import os
import time

from slackclient import SlackClient
from collections import defaultdict
from collections import deque

import wizardgame as WizardGame
import helper_functions

BOT_ID = os.environ.get("BOT_ID")
AT_BOT = "<@" + BOT_ID + ">"
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))

class WizardBot:
    def __init__(self, main_channel_id='C2F154UTE'):
        self.users_in_game = []
        self.user_ids_to_username = {}
        self.channel_ids_to_name = {}
        self.main_channel_id = 'C2F154UTE' #TODO make this dynamic
        self.player_bids_for_current_round = []
        self.listening_for_user_id = ""
        self.player_bid_queue = []
        self.player_turn_queue = []
        self.current_round = 1

    def handle_command(self, command, channel, user_id):
        #TODO restrict the channel this is in
        username = self.user_ids_to_username[user_id] #user who sent the message
        response = "Hey! So uh...this is awkward, but I only respond to game commands." #default response

        if command.lower().startswith("create game"):
            if len(self.users_in_game) == 0:
                response = "<@{}> Wants to play a game of wizard! Tell me `add me` to play.".format(username)
                self.users_in_game.append(user_id)
            else:
                response = "There's already a game being made, say `add me` if you want in."

        if command.lower().startswith("cancel"):
            response = "Okay, game cancelled."
            while len(self.users_in_game) > 0:
                self.users_in_game.pop()

        if command.lower().startswith("add me"):
            if len(self.users_in_game) == 0:
                response = "There is no active game, try `create game`."
            else:
                if user_id in self.users_in_game:
                    response = "You've already been added to the game."
                else:
                    self.users_in_game.append(user_id)
                    response = "Added <@{}> to the game!".format(username)

        if command.lower().startswith("start game"):
             #TODO this should be minimum for 3 players.
             #TODO is there a max number of players?
            if len(self.users_in_game) == 0:
                response = "No game exists yet. Try `create game`"

            elif len(self.users_in_game) < 2:
                response = "There aren't enough players yet (minimum 4). Users can say `add me` to be added to the game."
            else:
                response = "Starting a new game of Wizard with players: \n" + self.get_readable_list_of_players()
                self.play_game_of_wizard_on_slack(self.users_in_game, channel)

        slack_client.api_call("chat.postMessage", channel=channel,
                              text=response, as_user=True)

    def handle_private_message(self, command, user_id):
        response = ""
        if len(self.player_bid_queue):
            current_username = self.user_ids_to_username[self.player_bid_queue[0]]
            #we're waiting for the first player in queue to bid
            if user_id != self.player_bid_queue[0]:
                response = "We're still waiting on <@{}> to bid.".format(current_username)
            elif user_id == self.player_bid_queue[0]:
                #expected user to bid
                try:
                    if 0 > int(command) > self.current_round:
                        response = "You can't bid that amount!"
                    else:
                        self.player_bids_for_current_round.append(int(command))
                        response = "Bid recorded! Check the main channel."

                        slack_client.api_call(
                            "chat.postMessage",
                            channel=self.main_channel_id,
                            text="{} bids *<@{}>*.".format(current_username, int(command)),
                            as_user=True
                        )

                        self.player_bid_queue.popleft()
                        if len(self.player_bid_queue) == 0:
                            #everyone bidded
                            slack_client.api_call(
                                "chat.postMessage",
                                channel=self.main_channel_id,
                                text="All bids recorded, let's play!",
                                as_user=True
                            )
                        else:
                            #there are still people who need to bid, notify them
                            slack_client.api_call(
                                "chat.postMessage",
                                channel=self.player_bid_queue[0],
                                text="What's your bid for the round?",
                                as_user=True
                            )
                except:
                    response = "That wasn't a valid bid."

        slack_client.api_call(
            "chat.postMessage",
            channel=user_id,
            text=response,
            as_user=True
        )

    def parse_slack_output(self, slack_rtm_output):
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

    def get_bids_from_players(self, current_round, players):
        self.player_bid_queue = deque([player.id for player in players])
        self.current_round = current_round
        slack_client.api_call(
            "chat.postMessage",
            channel=self.player_bid_queue[0],
            text="What's your bid for the round?",
            as_user=True
        )

    def prompt_dealer_for_trump_suit(self, player_id):
        slack_client.api_call(
            "chat.postMessage",
            channel=player_id,
            text="please select index for trump suit \n [:diamonds:][:clubs:][:hearts:][:spades:]",
            as_user=True
        )

    def get_readable_list_of_players(self):
        #TODO refactor this with less mumbojumbo
        player_names = []
        printable_player_names = []
        for player_id in self.users_in_game:
            player_names.append(self.user_ids_to_username[player_id])
        for idx, player_name in enumerate(player_names):
            printable_player_names.append("{}) <@{}>".format(idx + 1, player_name))
        return (' \n ').join(printable_player_names)

    def display_cards_for_player_in_pm(self, player_id, cards):
        formatted_cards = helper_functions.format_cards_to_emojis(cards)
        slack_client.api_call(
            "chat.postMessage",
            channel=player_id,
            text="Your card(s): {}".format(formatted_cards),
            as_user=True
        )

    def announce_trump_card(self, trump_card):
        slack_client.api_call(
            "chat.postMessage",
            channel=self.main_channel_id,
            text="*Round 1* \n The trump card is: [{}:{}:]".format(trump_card[0], trump_card[1]
            ),
            as_user=True
        )

    #takes an array of player_ids and the channel the game request originated from
    def play_game_of_wizard_on_slack(self, players, channel):
        player_objects = []
        for player_id in players:
            player_objects.append(WizardGame.Player(player_id))

        game = WizardGame.Game(player_objects, bot)
        game.play_round()


if __name__ == "__main__":
    bot = WizardBot()
    READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose
    #grab user list and converts it to to a dict of ids to usernames
    api_call = slack_client.api_call("users.list")

    if api_call.get('ok'):
        users = api_call.get('members')
        for user in users:
            bot.user_ids_to_username[user['id']] = user['name']

        channels = slack_client.api_call("channels.list").get('channels')
        for channel in channels:
            bot.channel_ids_to_name[channel['id']] = channel['name']

    if slack_client.rtm_connect():
        print("WizardBot connected and running!")

        while True:
            command, channel, user = bot.parse_slack_output(slack_client.rtm_read())
            if command and channel:
                if channel not in bot.channel_ids_to_name.keys():
                    #this (most likely) means that this channel is a PM with the bot
                    bot.handle_private_message(command, user)
                else:
                    bot.handle_command(command, channel, user)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Invalid Slack token or bot ID?")
