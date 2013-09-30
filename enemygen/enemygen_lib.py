import random

def _select_random_item(items, exclude = ()):
    ''' Input: List of items. The items need to have attribute 'probability' of type int 
               Optional: Items to be excluded
        Output: Randomly selected item from the list, based on the item probability
    '''
    weight_total = 0
    for item in items:
        if item not in exclude:
            weight_total += item.probability
    n = random.randint(1, weight_total)
    for item in items:
        if item not in exclude:
            if n <= item.probability:
                break
            n -= item.probability
    return item
    
class ValidationError(Exception):
    pass

def to_bool(input):
    if isinstance(input, str) and (input.lower() == 'false' or input) == '':
        return False
    else: 
        return bool(input)
    

def replace_die_set(die_set, replace):
    ''' Replaces stat names in the die-set with actual values 
        Input is dict like {'STR': 12, 'SIZ': 16}
    '''
    for key, value in replace.items():
        die_set = die_set.replace(key, str(value))
    return die_set

def int_or_zero(value):
    if value == '': return 0
    return int(value)
        