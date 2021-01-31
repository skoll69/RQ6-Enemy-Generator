import random


def select_random_items(item_list, amount):
    """ Randomly selects the given amount of items from the given list
        Input: item_list: List of items where to pick from. The items on the list need to have the attribute
               'probability'
               amount: amount of items to be selected
    """
    output = []
    selected_items = []
    for x in range(amount):
        item = select_random_item(item_list, selected_items)
        selected_items.append(item)
        output.append(item)
    output.sort(key=lambda item: item.name)
    return output


def select_random_item(items, exclude=()):
    """ Input: List of items. The items need to have attribute 'probability' of type int 
               Optional: Items to be excluded
        Output: Randomly selected item from the list, based on the item probability
    """
    weight_total = 0
    for item in items:
        if item not in exclude:
            weight_total += item.probability
    n = random.randint(1, weight_total)
    for item in items:
        if item not in exclude:
            if n <= item.probability:
                return item
            n -= item.probability


class ValidationError(Exception):
    pass


def to_bool(text):
    if isinstance(text, str) and (text.lower() == 'false' or text) == '':
        return False
    else:
        return bool(text)
    

def replace_die_set(die_set, replace=None):
    """ Replaces stat names in the die-set with actual values 
        Input is dict like {'STR': 12, 'SIZ': 16}
    """
    if not replace:
        return die_set
    for key, value in replace.items():
        die_set = die_set.replace(key, str(value))
    return die_set
