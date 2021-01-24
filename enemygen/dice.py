"""
Handles dice.
"""

import random
import re
from collections import OrderedDict


class Dice:
    def __init__(self, dice_set):
        self.dice_set = dice_set.upper()
        self.components = self._dissect()
    
    def roll(self):
        output = 0
        for comp in self.components:
            if isinstance(comp, int):
                output += comp
            elif isinstance(comp, tuple):
                for i in range(comp[2]):
                    output += random.randint(comp[0], comp[1])
        return output
        
    def max_roll(self):
        output = 0
        for comp in self.components:
            if isinstance(comp, int):
                output += comp
            elif isinstance(comp, tuple):
                for i in range(comp[2]):
                    output += comp[1]
        return output

    def _dissect(self):
        """ Analyses the input string and splits it into dice roll components.
            Simple ints's will stay simple int's, dice are split into tuples of 
            three int's. For excample 10+D6 should result in [10, (1,6,1)]
        """
        raw_components = re.findall(r"[\+\-]?[\w']+", self.dice_set)
        fin_components = []
        for comp in raw_components:
            try:
                comp = int(comp)
            except ValueError:
                comp = _die_to_tuple(comp)
            fin_components.append(comp)
        return fin_components


def clean(dieset):
    """ Cleans the given dieset combining simila components. eg. STR+D10+1d10 bcomes STR+2d10 """
    dieset = dieset.replace('+-', '-')
    dieset = dieset.replace('-+', '-')
    dieset = dieset.upper()
    dieset = re.sub('D(\d)', r'd\1', dieset)    # Change Upper case D to lower case if it's part of a die (not DEX)
    components = re.findall(r"[\+\-]?[\w']+", dieset)
    if components[0][0] not in '+-':    # Prefix with plus if no prefix
        components[0] = '+' + components[0]
    new_components = OrderedDict()
    # Add the components to a dict, counting (dict value) each different component type
    static_int = 0  # Holds the cumulative value of static int components
    for comp in components:
        if 'd' in comp:  # It's a die, not stat (STR, DEX...)
            amount, die = comp.split('d')
            if amount == '+' or amount == '-':  # Change '+' to '+1', as in '+D6' > '+1D6'
                amount += '1'
            die = 'd'+die
            if die not in new_components:
                new_components[die] = 0
            new_components[die] += int(amount)
        else:   # Stat or a static number
            try:    # A static number
                static_int += int(comp)
            except ValueError:  # Stat, eg. STR, DEX
                amount = 1 if comp[0] == '+' else -1
                comp = comp[1:]
                if comp not in new_components:
                    new_components[comp] = 0
                new_components[comp] += amount
    out = ''
    for comp, amount in new_components.items():
        if amount == 0:
            continue
        if 'd' in comp: # It's a die
            amount = str(amount) if amount < 0 else '+' + str(amount)
            out += '%s%s' % (amount, comp)
        else:  # It's a stat
            sign = '+' if amount > 0 else '-'
            out += (sign+comp)*abs(amount)
    if static_int:
        out += str(static_int) if static_int < 0 else '+' + str(static_int)
    if out[0] == '+':
        out = out[1:]
    return out

def _invert_comp(comp):
    """ Inverts the sign (+ or -) of the given string component """
    if comp[0] == '-':
        return '+' + comp[1:]
    else:
        return '-' + comp[1:]


def _die_to_tuple(die):
    """ Takes a string representing a die (e.g. D6 or 3d8) as input.
        Gives out a tuple of three int's, where 
        output[0] is the starting range 
        output[1] is the end range and
        output[2] defines how many times the dice are rolled.
        For example:
          1D6: (1,6,1)
          3D8: (1,8,3)
          -2D10: (-10,-1,2)
    """
    die = die.upper()
    negative = False
    multiplier = 1
    if die[0] == '-':
        negative = True
    die = die.replace('-', '')
    die = die.replace('+', '')
    try:    # Check if the first character is a number, e.g. 3D6
        multiplier, die = die.split('D')
        if multiplier == '':
            multiplier = 1
        multiplier = int(multiplier)
    except ValueError:
        pass
    die = int(die)
    if negative:
        output = (-1*die, -1, multiplier)
    else:
        output = (1, die, multiplier)
    return output
