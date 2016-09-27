def format_cards_to_emojis(cards):
    formatted_cards = []
    for card in cards:
        if len(card) == 2:
            formatted_cards.append("[{}:{}:]".format(card[0],card[1]))
        else:
            formatted_cards.append(":{}:".format(card))
    return "".join(formatted_cards)
