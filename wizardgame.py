import random

wizard_deck = ["JE", "JE", "JE", "JE"]
suits = ["diamonds", "clubs", "hearts", "spades"]
values = [2, 3, 4, 5, 6, 7, 8, 9, 10, "J", "Q", "K", "A"]
for suit in suits:
    for value in values:
        wizard_deck.append([value, suit])
wizard_deck = wizard_deck + ["W", "W", "W", "W"]

def rotate_list(l, n):
    return l[-n:] + l[:-n]

class Player:
    def __init__(self, name):
        self.points = 0
        self.name = name
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
    def __init__(self, players):
        #[Player1, Player2, Player3, ...etc]
        self.players = players
        self.final_round = 60/len(players) #i.e. 12 rounds for 5 players
        self.current_round = 1

    def play_round(self):
        shuffled_deck = Deck()
        for _ in range(0, self.current_round):
            self.deal_single_card_to_each_player(shuffled_deck)

        #determine trump suit according to default rules
        if len(shuffled_deck.cards) > 0:
            trump_card = shuffled_deck.cards.pop()
            if trump_card == "W" or trump_card == "JE":
                #is a wizard or jester
                if trump_card == "W":
                    trump_suit = "W"
                    self.prompt_dealer_for_trump_suit()
                elif trump_card == "JE":
                    trump_suit = None
            elif len(trump_card) == 2: #regular card
                trump_suit = trump_card[1]
        elif len(shuffled_deck.cards) == 0:
            trump_suit = None
        #dealer is always index 0 of players and we will rotate the array end of each turn
        for _ in range(0, self.current_round):
            self.play_mini_round()

        self.current_round += 1


    def play_mini_round(self):
        player_bids = self.get_player_bids()
        #prompt each player to choose a card
        self.prompt_players_for_card_to_play()

    def deal_single_card_to_each_player(self, deck):
        for player in self.players:
            player.receive_card(deck.deal_card())

    def prompt_dealer_for_trump_suit(self):
        #either it's the last round or a wizard was the trump card
        pass

    def prompt_players_for_card_to_play(self):
        for player in players:
            pass #prompt player to choose a card

    def get_player_bids(self):
        for player in self.players:
            pass #TODO get player bid from slack PM

def get_list_of_players_who_are_down_for_a_game_of_wizard():
    pass

players = [Player("Dustin"), Player("Robert"), Player("Brian"), Player("Bryant")]
game = Game(players)
game.play_round()
