import random
import wizardbot as WizardBot

wizard_deck = ["jester", "jester", "jester", "jester"]
suits = ["diamonds", "clubs", "hearts", "spades"]
values = [2, 3, 4, 5, 6, 7, 8, 9, 10, "J", "Q", "K", "A"]
for suit in suits:
    for value in values:
        wizard_deck.append([value, suit])
wizard_deck = wizard_deck + ["wizard", "wizard", "wizard", "wizard"]

def rotate_list(l, n):
    return l[-n:] + l[:-n]

class Player:
    def __init__(self, id):
        self.points = 0
        self.id = id
        self.cards_in_hand = []

    def receive_card(self, card):
        self.cards_in_hand.append(card)

class Deck: #preshuffled deck
    def __init__(self):
        self.cards = wizard_deck[:]
        random.shuffle(self.cards)

    def deal_card(self):
        return self.cards.pop()

class Game:
    def __init__(self, players, bot):
        #[Player1, Player2, Player3, ...etc]
        self.players = players
        self.final_round = 60/len(players) #i.e. 12 rounds for 5 players
        self.current_round = 1
        self.current_round_trump_suit = None
        self.bot = bot
        self.bot.current_game = self

    # 1) creates a new shuffled deck
    # 2) deals cards to the players depending on the round #
    # 3) determines trump suit (or asks dealer for it)
    # 4) gets bids from players
    # 5) plays mini-rounds & allocates points until round is over
    def play_round(self):
        shuffled_deck = Deck()
        for _ in range(0, self.current_round):
            self.deal_single_card_to_each_player(shuffled_deck)

        #determine trump suit according to default rules
        if len(shuffled_deck.cards) > 0:
            trump_card = shuffled_deck.cards.pop()
            if trump_card == "wizard" or trump_card == "jester":
                #is a wizard or jester
                if trump_card == "wizard":
                    self.bot.prompt_dealer_for_trump_suit(self.players[0].id)
                    self.bot.player_trump_card_queue.append(self.players[0].id)
                elif trump_card == "jester":
                    trump_suit = None
            elif len(trump_card) == 2: #regular card
                trump_suit = trump_card[1]
        elif len(shuffled_deck.cards) == 0:
            self.bot.prompt_dealer_for_trump_suit(self.players.first.id)
        for player in self.players:
            self.bot.display_cards_for_player_in_pm(player.id, player.cards_in_hand)
        self.bot.get_bids_from_players(self.current_round, self.players)
        self.bot.announce_trump_card(trump_card)
        #dealer is always index 0 of players and we will rotate the array end of each turn

    def deal_single_card_to_each_player(self, deck):
        for player in self.players:
            player.receive_card(deck.deal_card())
