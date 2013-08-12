import random

def _select_random_spell(spells, exclude = ()):
    weight_total = 0
    for spell in spells:
        if spell not in exclude:
            weight_total += spell.probability
    n = random.randint(1, weight_total)
    for spell in spells:
        if spell not in exclude:
            if n <= spell.probability:
                break
            n -= spell.probability
    return spell
    
class ValidationError(Exception):
    pass

def to_bool(input):
    if isinstance(input, str) and (input.lower() == 'false' or input) == '':
        return False
    else: 
        return bool(input)
    
