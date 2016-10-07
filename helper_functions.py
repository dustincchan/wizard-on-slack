def format_cards_to_emojis(cards):
    formatted_cards = []
    for idx, card in enumerate(cards):
        if len(card) == 2:
            formatted_cards.append("`{}`[{}:{}:]  ".format(idx, card[0], card[1]))
        else:
            formatted_cards.append("`{}`:{}:  ".format(idx, card))
    return "".join(formatted_cards)

def emojify_card(card):
    if len(card) == 2:
        return "[{}:{}:]".format(card[0], card[1])
    else:
        return "[:{}:]".format(card)
