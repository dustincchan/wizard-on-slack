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
suits = ["diamonds", "clubs", "hearts", "spades"]

class WizardBot:
    def __init__(self, main_channel_id='C2F154UTE'):
        self.users_in_game = deque([]) #[user_id, user_id...]
        self.user_ids_to_username = {} #{'USERID': 'Dustin'}
        self.channel_ids_to_name = {} #{'CHANNELID': "#Maingame"}
        self.main_channel_id = 'C2F154UTE' #TODO make this dynamic
        self.player_bids_for_current_round = [] #[1, 1, 0]

        self.player_trump_card_queue = [] #['USERID']
        self.player_bid_queue = [] #['USERID1', 'USERID2', 'USERID3']
        self.player_turn_queue = [] #['USERID1', 'USERID2', 'USERID3']

        self.current_round = 1
        self.current_game = None #WizardGame.Game() object

        #this is the suit that enforces other players play a card that has that suit, if they have one
        self.sub_round_suit = None #"diamonds"
        self.cards_played_for_sub_round = [] #this mirrors player_turn_queue as to determine a winner
        self.winner_for_sub_round = None

    def handle_command(self, command, channel, user_id):
        #TODO restrict the channel this is in
        username = self.user_ids_to_username[user_id] #user who sent the message

        #TODO this response can come from a random array of responses to gibberish
        response = "Hey! So uh...this is awkward, but I only respond to game commands."

        if command.lower().startswith("debug game"):
            self.users_in_game.append('U2F0ZG8CW') #dustin
            self.users_in_game.append('U2FHWL0J0') #dustinphone
            # self.users_in_game.append('U2JAAKHD5') #dustinipad
            response = ">>>Starting a new game of Wizard with players: \n" + self.get_readable_list_of_players()
            slack_client.api_call("chat.postMessage", channel=channel,
                                  text=response, as_user=True)
            self.play_game_of_wizard_on_slack(self.users_in_game, channel)
            return


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
                response = ">>>Starting a new game of Wizard with players: \n" + self.get_readable_list_of_players()
                slack_client.api_call("chat.postMessage", channel=channel,
                                      text=response, as_user=True)
                self.play_game_of_wizard_on_slack(self.users_in_game, channel)
                return #have to do this because we want the "new game" message to come before the trump card announcement

        slack_client.api_call("chat.postMessage", channel=channel,
                              text=response, as_user=True)

    def handle_trump_suit_selection(command, user_id):
        response = ""
        current_username = self.user_ids_to_username[self.player_trump_card_queue[0]]
        #we're waiting for a user to select a trump card
        if user_id != self.player_trump_card_queue[0]:
            response = "Waiting for <@{}> to select a trump suit"
        elif user_id == self.player_trump_card_queue:
            #validate that the dealer picked a valid trump suit
            try:
                if 0 <= int(command) <= 3:
                    self.current_game.current_round_trump_suit = suits[int(command)]
                    response = "Trump suit recorded! Check the main channel."
                    slack_client.api_call(
                        "chat.postMessage",
                        channel=self.main_channel_id,
                        text="<@{}> chose :{}: for the trump suit.".format(current_username, suits[int(command)]),
                        as_user=True
                    )
                    self.private_message_user(self.player_bid_queue[0], "What's your bid for the round?")
                    self.player_trump_card_queue.pop()
                else:
                    response = "That wasn't a valid index for a trump suit."
            except:
                response = "That's not a valid command. Please select a trump suit."

        self.private_message_user(user_id, response)

    def get_card_being_played(self, user_id, index): # -> ex. ['A', 'spades']
        for user_object in self.current_game.players:
            if user_object.id == user_id:
                print(user_object.cards_in_hand)
                return user_object.cards_in_hand[index]

    def handle_player_bid(self, command, user_id):
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
                    #valid bid
                    self.player_bids_for_current_round.append(int(command))
                    response = "Bid recorded! Check the main channel."
                    slack_client.api_call(
                        "chat.postMessage",
                        channel=self.main_channel_id,
                        text="<@{}> bids `{}`.".format(current_username, int(command)),
                        as_user=True
                    )
                    self.player_bid_queue.popleft()
                    if len(self.player_bid_queue) == 0:
                        #everyone bidded, time to play sub_round
                        slack_client.api_call(
                            "chat.postMessage",
                            channel=self.main_channel_id,
                            text="All bids recorded, let's play!",
                            as_user=True
                        )
                        self.private_message_user(self.player_turn_queue[0], "Please select an card `index` to play.")
                    else: #get the next player's bid
                        self.private_message_user(self.player_bid_queue[0], "What's your bid for the round?")
            except:
                response = "That wasn't a valid bid."

        self.private_message_user(user_id, response)

    def handle_player_turn(self, command, user_id):
        response = ""
        current_username = self.user_ids_to_username[self.player_turn_queue[0]]
        print("User sending message: {}".format(self.user_ids_to_username[user_id]  ))
        #waiting for first player after dealer to play a card
        if user_id != self.player_turn_queue[0]:
            response = "Waiting for <@{}> to play a card.".format(current_username)
        elif user_id == self.player_turn_queue[0]:
            print('Received input from expected player')
            #validate the int(command) index selected is within the range of cards in hand
            if int(command) >= 0 and int(command) < self.current_round:
                card_being_played = self.get_card_being_played(user_id, int(command))
                #valid card played
                if self.sub_round_suit != None:
                    #a wizard or a jester is always a valid play
                    if card_being_played == "wizard" or card_being_played == "jester":
                        self.handle_valid_card_played(card_being_played)
                    elif self.sub_round_suit == "Any":
                        #a wizard was played as the first card
                        #players are free to play whatever they want
                        self.handle_valid_card_played(card_being_played)
                    elif card_being_played[1] == self.sub_round_suit:
                        #card played same suit as sub_round_suit
                        self.handle_valid_card_played(card_being_played)
                    elif self.player_hand_contains_suit(user_id, self.sub_round_suit) == False:
                        #any card is valid, because player doesn't have the initial suit
                        self.handle_valid_card_played(card_being_played)
                    else:
                        self.private_message_user(user_id, "You can't play that card")
                elif self.sub_round_suit == None:
                    if card_being_played == "wizard":
                        self.sub_round_suit = "Any"
                        self.handle_valid_card_played(card_being_played)
                    elif card_being_played == "jester":
                        #the sub round suit stays None until a player plays a suited card
                        self.handle_valid_card_played(card_being_played)
                    else:
                        self.sub_round_suit = card_being_played[1]
                        self.cards_played_for_sub_round.append(card_being_played)
            else:
                response = "That wasn't a valid card index."
        self.private_message_user(user_id, response)

    def player_hand_contains_suit(user_id, suit):
        for user_object in self.current_game.players:
            if user_object.id == user_id:
                for card in user_object.cards_in_hand:
                    if card != "wizard" and card != "jester":
                        if card[1] == suit:
                            return True
        return False


    def handle_valid_card_played(self, card):
        print("Player turn queue: {}".format(self.player_turn_queue))
        self.cards_played_for_sub_round.append(card)
        self.player_turn_queue.popleft()
        if len(self.player_turn_queue) == 0:
            #everyone has played the sub_round
            print("Card played: {}".format(self.cards_played_for_sub_round))
            self.determine_winner_for_sub_round()
        else:
            self.private_message_user(self.player_turn_queue[0], "Your turn. Pick a card to play.")

    def determine_winner_for_sub_round():
        pass #goes through the cards played

    def message_main_game_channel(self, message):
        slack_client.api_call(
            "chat.postMessage",
            channel=self.main_channel_id,
            text=message,
            as_user=True
        )

    def private_message_user(self, user_id, message):
        slack_client.api_call(
            "chat.postMessage",
            channel=user_id,
            text=message,
            as_user=True
        )


    def handle_private_message(self, command, user_id):
        response = ""
        if len(self.player_trump_card_queue):
            # self.handle_trump_suit_selection(command, user_id)
            print('TODO: handle trump suit selection')

        elif len(self.player_bid_queue):
            self.handle_player_bid(command, user_id)

        elif len(self.player_turn_queue):
            self.handle_player_turn(command, user_id)


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
        self.player_turn_queue = deque([player.id for player in players])
        #the player after the dealer should be first to bid, so we rotate the queue
        self.player_bid_queue.rotate(-1)
        self.player_turn_queue.rotate(-1)
        self.users_in_game.rotate(-1)
        self.current_round = current_round

        #DEBUGGING REMOVE THIS AFTER TESTING
        self.player_bid_queue.clear()
        self.player_bids_for_current_round = [1 ,1]
        slack_client.api_call(
            "chat.postMessage",
            channel=self.main_channel_id,
            text="DEBUG MODE: GOT BIDS AUTOMATICALLY BY DEBUGGING",
            as_user=True
        )
        #DEBUGGING

        # slack_client.api_call(
        #     "chat.postMessage",
        #     channel=self.player_bid_queue[0],
        #     text="What's your bid for the round?",
        #     as_user=True
        # )

    def prompt_dealer_for_trump_suit(self, player_id):
        self.player_trump_card_queue.append(player_id)
        slack_client.api_call(
            "chat.postMessage",
            channel=player_id,
            text="please select index for trump suit \n `0`[:diamonds:]   `1`[:clubs:]   `2`[:hearts:]   `3`[:spades:]",
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
            text=">>>*Round {}* \n The trump card is: [{}:{}:]".format(self.current_round, trump_card[0], trump_card[1]),
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
    READ_WEBSOCKET_DELAY = 0.25 # 1 second delay between reading from firehose
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
