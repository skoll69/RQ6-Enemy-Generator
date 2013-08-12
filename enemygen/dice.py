'''
Handles dice.
'''

import random, re

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
        ''' Analyses the input string and splits it into dice roll components.
            Simple ints's will stay simple int's, dice are split into tuples of 
            two int's. For excample 10+D6 should result in [10, (1,6,1)]'''
        raw_components = re.findall(r"[\+\-]?[\w']+", self.dice_set)
        fin_components = []
        for comp in raw_components:
            try:
                comp = int(comp)
            except ValueError:
                comp = _die_to_tuple(comp)
            fin_components.append(comp)
        return fin_components

def _die_to_tuple(die):
    ''' Takes a string representing a die (e.g. D6 or 3d8) as input.
        Gives out a tuple of three int's, where 
        output[0] is the starting range 
        output[1] is the end range and
        output[2] defines how many times the dice are rolled.
        For example:
          1D6: (1,6,1)
          3D8: (1,8,3)
          -2D10: (-10,-1,2)
        '''
    die = die.upper()
    negative = False
    multiplier = 1
    if die[0] == '-': negative = True
    die = die.replace('-', '')
    die = die.replace('+', '')
    try:    # Check if the first character is a number, e.g. 3D6
        multiplier = int(die[0])
        die = die[1:]
    except ValueError:
        pass
    die = die.replace('D', '')
    die = int(die)
    if negative:
        output = (-1*die, -1, multiplier)
    else:
        output = (1, die, multiplier)
    return output
    