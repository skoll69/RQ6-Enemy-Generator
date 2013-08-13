from django.db import models
from django.contrib.auth.models import User

from enemygen_lib import _select_random_item, ValidationError

from dice import Dice

import ordereddict
import random

class Printer:
    def __unicode__(self):
        return self.name
        
class Setting(models.Model, Printer):
    name = models.CharField(max_length=30)
    owner = models.ForeignKey(User)
    
class Ruleset(models.Model, Printer):
    name = models.CharField(max_length=30)
    owner = models.ForeignKey(User)
    stats = models.ManyToManyField('StatAbstract', null=True, blank=True)
    skills = models.ManyToManyField('SkillAbstract', null=True, blank=True)
    races = models.ManyToManyField('Race', null=True, blank=True)
        
class Weapon(models.Model, Printer):
    name = models.CharField(max_length=50)
    damage = models.CharField(max_length=30, default=0)
    type_choices = (
                ('1h-melee', '1-h Melee'),
                ('2h-melee', '2-h Melee'),
                ('ranged', 'Ranged'),
                ('shield', 'Shield'),
                )
    type = models.CharField(max_length=30, choices=type_choices)
    size_choices = (
                        ('S', 'S'),
                        ('M', 'M'),
                        ('L', 'L'),
                        ('H', 'H'),
                        ('E', 'E'),
                    )
    size = models.CharField(max_length=1, choices=size_choices)
    reach_choices = (
                        ('-', '-'),
                        ('T', 'T'),
                        ('S', 'S'),
                        ('M', 'M'),
                        ('L', 'L'),
                        ('VL', 'VL'),
                    )
    reach = models.CharField(max_length=2, choices=reach_choices)
    ap = models.SmallIntegerField(default=0)
    hp = models.SmallIntegerField(default=0)
    damage_modifier = models.BooleanField(default=False)
        
class Race(models.Model, Printer):
    name = models.CharField(max_length=30)
    owner = models.ForeignKey(User)
    movement = models.SmallIntegerField(default=6)
    special = models.TextField(blank=True)
    
    class Meta:
        ordering = ['name',]
        
    @property
    def hit_locations(self):
        return HitLocation.objects.filter(race=self)

    @property
    def stats(self):
        return RaceStat.objects.filter(race=self)

class HitLocation(models.Model, Printer):
    name = models.CharField(max_length=30)
    natural_armor = models.SmallIntegerField(default=0)
    range_start = models.SmallIntegerField()
    range_end = models.SmallIntegerField()
    race = models.ForeignKey(Race)
    hp_modifier = models.SmallIntegerField(default=0)
    
    class Meta:
        ordering = ['range_start',]
        
    @property
    def range(self):
        if self.range_start == self.range_end:
            return '%02d' % self.range_start
        else:
            return '%02d-%02d' % (self.range_start, self.range_end)
    
class EnemyTemplate(models.Model, Printer):
    name = models.CharField(max_length=50)
    owner = models.ForeignKey(User)
    setting = models.ForeignKey(Setting)
    ruleset = models.ForeignKey(Ruleset)
    race = models.ForeignKey(Race)
    folk_spell_amount = models.CharField(max_length=30, null=True, blank=True, default='0')
    theism_spell_amount = models.CharField(max_length=30, null=True, blank=True, default='0')
    sorcery_spell_amount = models.CharField(max_length=30, null=True, blank=True, default='0')
    generated = models.IntegerField(default=0)
    published = models.BooleanField(default=False)
    rank_choices = ((1, 'Rubble'), (2, 'Novice'), (3, 'Skilled'), (4, 'Veteran'), (5, 'Master'))
    rank = models.SmallIntegerField(max_length=30, default=2, choices=rank_choices)
    
    @classmethod
    def create(cls, owner, ruleset, setting, race, name="Enemy Template"):
        enemy_template = cls(name=name, owner=owner, ruleset=ruleset, setting=setting, race=race)
        enemy_template.save()
        if name == 'Enemy Template':
            enemy_template.name = '%s Template %s' % (race.name, enemy_template.id)
            enemy_template.save()
        for stat in race.stats:
            es = EnemyStat(stat=stat.stat, enemy_template=enemy_template, die_set=stat.default_value)
            es.save()
        for skill in ruleset.skills.all():
            es = EnemySkill(skill=skill, enemy_template=enemy_template, die_set=skill.default_value, include=skill.include)
            es.save()
        for hit_location in race.hit_locations:
            ehl = EnemyHitLocation(hit_location=hit_location, enemy_template=enemy_template)
            ehl.save()
        cs = CombatStyle(name="Primary Combat Style", enemy_template=enemy_template)
        cs.save()
        return enemy_template

    def generate(self, suffix=None):
        self.generated += 1
        self.save()
        return _Enemy(self).generate(suffix)

    @property
    def stats(self):
        return EnemyStat.objects.filter(enemy_template=self)

    @property
    def skills(self):
        return EnemySkill.objects.filter(enemy_template=self)
        
    @property
    def included_standard_skills(self):
        return EnemySkill.objects.filter(enemy_template=self, skill__standard=True, include=True)
        
    @property
    def standard_skills(self):
        return EnemySkill.objects.filter(enemy_template=self, skill__standard=True)
        
    @property
    def included_professional_skills(self):
        return EnemySkill.objects.filter(enemy_template=self, skill__standard=False, include=True)
        
    @property
    def professional_skills(self):
        return EnemySkill.objects.filter(enemy_template=self, skill__standard=False)
        
    #@property
    #def spells(self):
    #    return EnemySpell.objects.filter(enemy_template=self)

    @property
    def folk_spells(self):
        output = []
        output.extend(list(EnemySpell.objects.filter(enemy_template=self, spell__type="folk")))
        output.extend(list(CustomSpell.objects.filter(enemy_template=self, type="folk")))
        return output

    @property
    def theism_spells(self):
        output = []
        output.extend(list(EnemySpell.objects.filter(enemy_template=self, spell__type="theism")))
        output.extend(list(CustomSpell.objects.filter(enemy_template=self, type="theism")))
        return output

    @property
    def sorcery_spells(self):
        output = []
        output.extend(list(EnemySpell.objects.filter(enemy_template=self, spell__type="sorcery")))
        output.extend(list(CustomSpell.objects.filter(enemy_template=self, type="sorcery")))
        return output

    @property
    def hit_locations(self):
        return EnemyHitLocation.objects.filter(enemy_template=self)

    @property
    def combat_styles(self):
        return CombatStyle.objects.filter(enemy_template=self)

class CombatStyle(models.Model):
    name = models.CharField(max_length=30)
    die_set = models.CharField(max_length=30, default="STR+DEX")
    enemy_template = models.ForeignKey(EnemyTemplate)
    weapon_options = models.ManyToManyField(Weapon, null=True, blank=True)
    one_h_amount = models.SmallIntegerField(default=0)
    two_h_amount = models.SmallIntegerField(default=0)
    ranged_amount = models.SmallIntegerField(default=0)
    shield_amount = models.SmallIntegerField(default=0)
    
    @property
    def one_h_weapon_options(self):
        return self.weapon_options.filter(type='1h-melee')
        
    @property
    def two_h_weapon_options(self):
        return self.weapon_options.filter(type='2h-melee')
        
    @property
    def ranged_weapon_options(self):
        return self.weapon_options.filter(type='ranged')
        
    @property
    def shield_options(self):
        return self.weapon_options.filter(type='shield')
        
    def roll(self, replace):
        die_set = self._replaced_die_set(replace)
        dice = Dice(die_set)
        return dice.roll()
        
    def _replaced_die_set(self, replace):
        ''' Replaces stat names in the die-set with actual values 
            Input is dict like {'STR': 12, 'SIZ': 16}
        '''
        die_set = self.die_set
        for key, value in replace.items():
            die_set = die_set.replace(key, str(value))
        return die_set
        
class EnemyWeapon(models.Model, Printer):
    ''' Enemy-specific instance of a Weapon. Links selected weapon to CombatStyle and records
        Probability.
    '''
    combat_style = models.ForeignKey(CombatStyle)
    weapon = models.ForeignKey(Weapon)
    probability = models.SmallIntegerField(default=1)
    
    #def __getattr__(self, attr):
    #    jalla = self.weapon
    #    return self.weapon.__dict_[attr]
        #return getattr(self.weapon, attr)
    
    @property
    def name(self):
        return self.weapon.name
        
    @property
    def type(self):
        return self.weapon.type
        
    @property
    def damage(self):
        return self.weapon.damage
        
    @property
    def size(self):
        return self.weapon.size
        
    @property
    def reach(self):
        return self.weapon.reach
        
    @property
    def ap(self):
        return self.weapon.ap
        
    @property
    def hp(self):
        return self.weapon.hp
        
    @property
    def damage_modifier(self):
        return self.weapon.damage_modifier
        
    def set_probability(self, value):
        self.probability = value
        self.save()
        if value == 0:
            self.delete()
            
    @classmethod
    def create(cls, combat_style, weapon, probability):
        ew = EnemyWeapon(combat_style=combat_style, weapon=weapon, probability=probability)
        ew.save()
        return ew
        
class SkillAbstract(models.Model, Printer):
    name = models.CharField(max_length=30)
    standard = models.BooleanField(default=True)
    default_value = models.CharField(max_length=30, blank=True)
    include = models.BooleanField()

    class Meta:
        ordering = ['name',]
    
class EnemySkill(models.Model, Printer):
    skill = models.ForeignKey(SkillAbstract)
    enemy_template = models.ForeignKey(EnemyTemplate)
    die_set = models.CharField(max_length=30, blank=True)
    include = models.BooleanField()
    
    class Meta:
        ordering = ['skill',]
    
    @property
    def name(self):
        return self.skill.name
        
    def roll(self, replace={}):
        die_set = self._replaced_die_set(replace)
        dice = Dice(die_set)
        return dice.roll()
        
    def set_value(self, value):
        self.die_set = value
        self.save()
        
    def _replaced_die_set(self, replace):
        ''' Replaces stat names in the die-set with actual values 
            Input is dict like {'STR': 12, 'SIZ': 16}
        '''
        die_set = self.die_set
        for key, value in replace.items():
            die_set = die_set.replace(key, str(value))
        return die_set
        
class EnemyHitLocation(models.Model, Printer):
    hit_location = models.ForeignKey(HitLocation)
    enemy_template = models.ForeignKey(EnemyTemplate)
    armor = models.CharField(max_length=30, blank=True) # die_set
    
    class Meta:
        ordering = ['hit_location',]
    
    @property
    def name(self):
        return self.hit_location.name
        
    @property
    def range(self):
        return self.hit_location.range

    @property
    def hp_modifier(self):
        return self.hit_location.hp_modifier

    def roll(self):
        dice = Dice(self.armor)
        return dice.roll()
        
    def set_armor(self, value):
        Dice(value).roll()  #Test that the value is valid
        self.armor = value
        self.save()
        
class StatAbstract(models.Model, Printer):
    name = models.CharField(max_length=30)
    order = models.SmallIntegerField(null=True)
    
    class Meta:
        ordering = ['order',]
        
class RaceStat(models.Model, Printer):
    stat = models.ForeignKey(StatAbstract)
    race = models.ForeignKey(Race)
    default_value = models.CharField(max_length=30, null=True)
    
    class Meta:
        ordering = ['stat',]

    @property
    def name(self):
        return self.stat.name
        
    def set_value(self, value):
        #Test that the value is valid
        Dice(value).roll()
        self.die_set = value
        self.save()
        
class EnemyStat(models.Model, Printer):
    stat = models.ForeignKey(StatAbstract)
    enemy_template = models.ForeignKey(EnemyTemplate)
    die_set = models.CharField(max_length=30, null=True)
    
    class Meta:
        ordering = ['stat',]
    
    @property
    def name(self):
        return self.stat.name
        
    def roll(self):
        dice = Dice(self.die_set)
        return dice.roll()

    def set_value(self, value):
        Dice(value).roll()  #Test that the value is valid
        self.die_set = value
        self.save()
        
class SpellAbstract(models.Model, Printer):
    ''' A Spell. '''
    name = models.CharField(max_length=30)
    
    choices = (
                ('folk', 'Folk magic'),
                ('theism', 'Theism'),
                ('sorcery', 'Sorcery'),
                )
    type = models.CharField(max_length=30, choices=choices)
    detail = models.BooleanField(default=False)
    default_detail = models.CharField(max_length=30, null=True, blank=True)
    
    class Meta:
        ordering = ['name',]
    
class EnemySpell(models.Model, Printer):
    ''' Enemy-specific instance of a SpellAbstract '''
    spell = models.ForeignKey(SpellAbstract)
    enemy_template = models.ForeignKey(EnemyTemplate)
    probability = models.SmallIntegerField(default=0)
    detail = models.CharField(max_length=30, null=True, blank=True)
        
    class Meta:
        ordering = ['spell',]
    
    @property
    def name(self):
        return self.spell.name

    @property
    def type(self):
        return self.spell.type
        
    def set_probability(self, value):
        self.probability = value
        self.save()
        if value == 0:
            self.delete()

class CustomSpell(models.Model, Printer):
    ''' Custom spells created by users '''
    enemy_template = models.ForeignKey(EnemyTemplate)
    name = models.CharField(max_length=30)
    probability = models.SmallIntegerField(default=0)
    type = models.CharField(max_length=30, choices=(('folk', 'Folk magic'),
                                                    ('theism', 'Theism'),
                                                    ('sorcery', 'Sorcery'),
                                                    ))

    @classmethod
    def create(cls, et_id, type):
        et = EnemyTemplate.objects.get(id=et_id)
        cs = cls(enemy_template=et, type=type, name='Custom spell', probability=1)
        cs.save()
        return cs
    
    def set_probability(self, value):
        self.probability = value
        self.save()
        if value == 0:
            self.delete()

    class Meta:
        ordering = ['name',]

class _Enemy:
    ''' Enemy instance created based on an EnemyTemplate. This is the stuff that gets printed
        for the user when Generate is clicked.
    '''
    def __init__(self, enemy_template):
        self.name = ''
        self.et = enemy_template
        self.stats = ordereddict.OrderedDict()
        self.stats_list = []
        self.skills = []
        self.folk_spells = []
        self.theism_spells = []
        self.sorcery_spells = []
        self.hit_locations = []
        self.template = enemy_template.name
        self.attributes = {}
        self.combat_styles = []

    def generate(self, suffix=None):
        self.name = self.et.name
        if suffix:
            self.name += ' %s' % suffix
        for stat in self.et.stats:
            self.stats[stat.name] = stat.roll()
            self.stats_list.append({'name': stat.name, 'value': self.stats[stat.name]})
        for skill in self.et.skills:
            if skill.include:
                self.skills.append({'name': skill.name, 'value': skill.roll(self.stats)})
        self._add_spells()
        self._calculate_attributes()
        self._add_hit_locations()
        self._add_combat_styles()
        return self
        
    @property
    def get_stats(self):
        return self.stats_list
        
    def _add_combat_styles(self):
        for cs in self.et.combat_styles:
            combat_style = {}
            combat_style['value'] = cs.roll(self.stats)
            combat_style['name'] = cs.name
            combat_style['weapons'] = self._add_weapons(cs)
            self.combat_styles.append(combat_style)
            
    def _add_weapons_old(self, cs):
        ''' Takes CombatStyle as input
            Returns a list of weapons
        '''
        weapons = []
        one_h_weapons = self._select_weapon_from_list(list(cs.one_h_weapon_options.all()))
        if one_h_weapons: weapons.append(one_h_weapons)
        two_h_weapons = self._select_weapon_from_list(list(cs.two_h_weapon_options.all()))
        if two_h_weapons: weapons.append(two_h_weapons)
        ranged_weapons = self._select_weapon_from_list(list(cs.ranged_weapon_options.all()))
        if ranged_weapons: weapons.append(ranged_weapons)
        shields = self._select_weapon_from_list(list(cs.shield_options.all()))
        if shields: weapons.append(shields)
        return weapons
        
    def _select_weapon_from_list(self, weapon_list):
        amount = len(weapon_list)
        if amount:
            index = random.randint(0, amount-1)
            weapon = weapon_list[index]
            return weapon
            
    def _add_weapons(self, cs):
        ''' Returns a list of weapons based on the given CombatStyle's weapon selections and probabilities
        '''
        output = []
        one_h_options = list(EnemyWeapon.objects.filter(weapon__type='1h-melee', combat_style=cs))
        two_h_options = list(EnemyWeapon.objects.filter(weapon__type='2h-melee', combat_style=cs))
        ranged_options = list(EnemyWeapon.objects.filter(weapon__type='ranged', combat_style=cs))
        shield_options = list(EnemyWeapon.objects.filter(weapon__type='shield', combat_style=cs))
        one_h_amount = min(cs.one_h_amount, len(one_h_options))
        two_h_amount = min(cs.two_h_amount, len(two_h_options))
        ranged_amount = min(cs.ranged_amount, len(ranged_options))
        shield_amount = min(cs.shield_amount, len(shield_options))
        output.extend(self._get_items(one_h_options, one_h_amount))
        output.extend(self._get_items(two_h_options, two_h_amount))
        output.extend(self._get_items(ranged_options, ranged_amount))
        output.extend(self._get_items(shield_options, shield_amount))
        return output
        
    def _add_hit_locations(self):
        for hl in self.et.hit_locations:
            con_siz = self.stats['CON'] + self.stats['SIZ']
            base_hp = ((con_siz-1) / 5) + 1 # used by Head and Legs
            hp = base_hp + hl.hp_modifier
            ap = hl.roll()
            enemy_hl = {'name': hl.name, 'range': hl.range, 'hp': hp, 'ap': ap}
            self.hit_locations.append(enemy_hl)
        
    def _add_hit_locations_old(self):
        for hl in self.et.race.hit_locations:
            con_siz = self.stats['CON'] + self.stats['SIZ']
            base_hp = ((con_siz-1) / 5) + 1 # used by Head and Legs
            hp = base_hp + hl.hp_modifier
            ap = 0
            enemy_hl = {'name': hl.name, 'range': hl.range, 'hp': hp, 'ap': ap}
            self.hit_locations.append(enemy_hl)
        
    def _add_spells(self):
        amount = min(Dice(self.et.folk_spell_amount).roll(), len(self.et.folk_spells))
        self.folk_spells = self._get_items(self.et.folk_spells, amount)
        
        amount = min(Dice(self.et.theism_spell_amount).roll(), len(self.et.theism_spells))
        self.theism_spells = self._get_items(self.et.theism_spells, amount)
        
        amount = min(Dice(self.et.sorcery_spell_amount).roll(), len(self.et.sorcery_spells))
        self.sorcery_spells = self._get_items(self.et.sorcery_spells, amount)
        
    def _get_items(self, item_list, amount):
        ''' Randomly selects the given amount of spells from the given list 
            Input: item_list: List of items where to pick from. The items need to have the attribute
                   'probability'
                   amount: amount of items to be selected
        '''
        output = []
        selected_items = []
        for x in range(amount):
            item = _select_random_item(item_list, selected_items)
            selected_items.append(item)
            output.append(item)
        output.sort()
        return output
        
    def _calculate_attributes(self):
        self._calculate_action_points()
        self._calculate_damage_modifier()
        self.attributes['magic_points'] = self.stats['POW']
        self.attributes['strike_rank'] = '+' + str((self.stats['INT'] + self.stats['DEX']) / 2)
        self.attributes['movement'] = self.et.race.movement
    
    def _calculate_action_points(self):
        dex_int = self.stats['DEX'] + self.stats['INT']
        if dex_int <= 12: self.attributes['action_points'] = 1
        elif dex_int <= 24: self.attributes['action_points'] = 2
        elif dex_int <= 36: self.attributes['action_points'] = 3
        elif dex_int <= 48: self.attributes['action_points'] = 4
        
    def _calculate_damage_modifier(self):
        DICE_STEPS = ('-1D8', '-1D6', '-1D4', '-1D2', '+0', '+1D2', '+1D4', '+1D6', '+1D8', '+1D10', '+1D12',
                      '+2D6', '+1D8+1D6', '+2D8', '+1D10+1D8', '+2D10', '+2D10+1D2', '+2D10+1D4', '+2D10+1D6')
        str_siz = self.stats['STR'] + self.stats['SIZ']
        if str_siz <= 50:
            index = (str_siz-1) / 5
        else:
            index = ((str_siz - 1 - 50) / 10) + 10
        self.attributes['damage_modifier'] = DICE_STEPS[index]
        

        
# DB modifications
# EnemyWeapon model
# CombatStyle: 4 amount fields
# CombatStyle poista weapon options