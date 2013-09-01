from django.db import models
from django.contrib.auth.models import User

from enemygen_lib import _select_random_item, ValidationError, replace_die_set

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
    name = models.CharField(max_length=80)
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
    published = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['name',]
        
    @property
    def hit_locations(self):
        return HitLocation.objects.filter(race=self)

    @property
    def stats(self):
        return RaceStat.objects.filter(race=self)
        
    @classmethod
    def create(cls, owner, name="New race"):
        race = cls(name=name, owner=owner)
        race.save()
        for stat in StatAbstract.objects.all():
            rs = RaceStat(stat=stat, race=race, default_value='3D6')
            rs.save()
        hl = HitLocation(name='Right leg', range_start=1, range_end=3, race=race, hp_modifier=0); hl.save()
        hl = HitLocation(name='Left leg', range_start=4, range_end=6, race=race, hp_modifier=0); hl.save()
        hl = HitLocation(name='Abdomen', range_start=7, range_end=9, race=race, hp_modifier=1); hl.save()
        hl = HitLocation(name='Chest', range_start=10, range_end=12, race=race, hp_modifier=2); hl.save()
        hl = HitLocation(name='Right Arm', range_start=13, range_end=15, race=race, hp_modifier=-1); hl.save()
        hl = HitLocation(name='Left Arm', range_start=16, range_end=18, race=race, hp_modifier=-1); hl.save()
        hl = HitLocation(name='Head', range_start=19, range_end=20, race=race, hp_modifier=0); hl.save()
        return race
        
    def set_published(self, published):
        if not published:
            self.published = published
            self.save()
            return
        # Add validation
        covered = []
        for hl in self.hit_locations:
            covered.extend(range(hl.range_start, hl.range_end+1))
        ok = True
        for x in range(1, 21): #Iterate through 1-20
            if x not in covered:
                ok = False
        if ok:
            self.published = published
            self.save()
        else:
            raise ValidationError

class HitLocation(models.Model, Printer):
    name = models.CharField(max_length=30)
    armor = models.CharField(max_length=30, blank=True, default='0') # die_set
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
            
    @classmethod
    def create(cls, race_id):
        biggest_range = 1
        race = Race.objects.get(id=race_id)
        for hl in HitLocation.objects.filter(race=race):
            biggest_range = max(hl.range_end, biggest_range)
        range_start = min(biggest_range+1, 20)
        range_end = min(biggest_range+3, 20)
        hl = HitLocation(name='New hit location', range_start=range_start, range_end=range_end, race=race)
        hl.save()
        return hl
        
    def set_armor(self, value):
        Dice(value).roll()  #Test that the value is valid
        self.armor = value
        self.save()
    
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
    rank_choices = ((1, 'Rabble'), (2, 'Novice'), (3, 'Skilled'), (4, 'Veteran'), (5, 'Master'))
    rank = models.SmallIntegerField(max_length=30, default=2, choices=rank_choices)
    movement = models.SmallIntegerField(default=6)
    notes = models.TextField(null=True, blank=True)
    
    @classmethod
    def create(cls, owner, ruleset, setting, race, name="Enemy Template"):
        enemy_template = cls(name=name, owner=owner, ruleset=ruleset, setting=setting, race=race)
        enemy_template.movement = race.movement
        enemy_template.notes = race.special
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
            EnemyHitLocation.create(hit_location, enemy_template)
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
        output = []
        output.extend(list(EnemySkill.objects.filter(enemy_template=self)))
        output.extend(list(CustomSkill.objects.filter(enemy_template=self)))
        output = sorted(output, key=lambda k: k.name)
        return output
        
    @property
    def included_standard_skills(self):
        return EnemySkill.objects.filter(enemy_template=self, skill__standard=True, include=True)
        
    @property
    def raw_skills(self):
        return EnemySkill.objects.filter(enemy_template=self)
        
    @property
    def standard_skills(self):
        return EnemySkill.objects.filter(enemy_template=self, skill__standard=True)
        
    @property
    def included_professional_skills(self):
        return EnemySkill.objects.filter(enemy_template=self, skill__standard=False, include=True)
        
    @property
    def professional_skills(self):
        return EnemySkill.objects.filter(enemy_template=self, skill__standard=False)
        
    @property
    def included_custom_skills(self):
        return CustomSkill.objects.filter(enemy_template=self, include=True)
        
    @property
    def custom_skills(self):
        return CustomSkill.objects.filter(enemy_template=self)
        
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
        
    def clone(self, owner):
        name = "Copy of %s" % self.name
        new = EnemyTemplate(owner=owner, ruleset=self.ruleset, setting=self.setting, race=self.race, name=name)
        new.movement = self.movement
        new.rank = self.rank
        new.folk_spell_amount = self.folk_spell_amount
        new.theism_spell_amount = self.theism_spell_amount
        new.sorcery_spell_amount = self.sorcery_spell_amount
        new.notes = self.notes
        new.save()
        for stat in self.stats:
            es = EnemyStat(stat=stat.stat, enemy_template=new, die_set=stat.die_set); es.save()
        for hl in self.hit_locations:
            new_hl = EnemyHitLocation.create(hl.hit_location, enemy_template=new, armor=hl.armor)
        for skill in self.raw_skills:
            es = EnemySkill(skill=skill.skill, enemy_template=new, die_set=skill.die_set, include=skill.include)
            es.save()
        for skill in self.custom_skills:
            es = CustomSkill(name=skill.name, enemy_template=new, die_set=skill.die_set, include=skill.include)
            es.save()
        for combat_style in self.combat_styles:
            combat_style.clone(new)
        for spell in EnemySpell.objects.filter(enemy_template=self):
            s = EnemySpell(enemy_template=new, spell=spell.spell, probability=spell.probability, detail=spell.detail)
            s.save()
        for spell in CustomSpell.objects.filter(enemy_template=self):
            s = CustomSpell(enemy_template=new, name=spell.name, probability=spell.probability, type=spell.type)
            s.save()
        return new

    def apply_skill_bonus(self, bonus):
        # Validate bonus
        replace = {'STR': 0, 'SIZ': 0, 'CON': 0, 'INT': 0, 'DEX': 0, 'POW': 0, 'CHA': 0}
        temp_value = replace_die_set(bonus, replace)
        Dice(temp_value).roll()
        
        if bonus[0] != '+':
            bonus = '+' + bonus
            
        for skill in self.raw_skills:
            skill.die_set = skill.die_set + bonus
            skill.save()
        for skill in self.custom_skills:
            skill.die_set = skill.die_set + bonus
            skill.save()
        for combat_style in self.combat_styles:
            combat_style.die_set = combat_style.die_set + bonus
            combat_style.save()
        
class CombatStyle(models.Model):
    name = models.CharField(max_length=80)
    die_set = models.CharField(max_length=30, default="STR+DEX")
    enemy_template = models.ForeignKey(EnemyTemplate)
    one_h_amount = models.CharField(max_length=30, default='0')
    two_h_amount = models.CharField(max_length=30, default='0')
    ranged_amount = models.CharField(max_length=30, default='0')
    shield_amount = models.CharField(max_length=30, default='0')
    
    def roll_one_h_amount(self):
        return Dice(self.one_h_amount).roll()
    
    def roll_two_h_amount(self):
        return Dice(self.two_h_amount).roll()
    
    def roll_shield_amount(self):
        return Dice(self.shield_amount).roll()
    
    def roll_ranged_amount(self):
        return Dice(self.ranged_amount).roll()
    
    @property
    def one_h_options(self):
        output = list(EnemyWeapon.objects.filter(weapon__type='1h-melee', combat_style=self))
        output.extend(list(CustomWeapon.objects.filter(type='1h-melee', combat_style=self)))
        return output
        
    @property
    def two_h_options(self):
        output = list(EnemyWeapon.objects.filter(weapon__type='2h-melee', combat_style=self))
        output.extend(list(CustomWeapon.objects.filter(type='2h-melee', combat_style=self)))
        return output
        
    @property
    def ranged_options(self):
        output = list(EnemyWeapon.objects.filter(weapon__type='ranged', combat_style=self))
        output.extend(list(CustomWeapon.objects.filter(type='ranged', combat_style=self)))
        return output
        
    @property
    def shield_options(self):
        output = list(EnemyWeapon.objects.filter(weapon__type='shield', combat_style=self))
        output.extend(list(CustomWeapon.objects.filter(type='shield', combat_style=self)))
        return output
        
    def roll(self, replace):
        die_set = replace_die_set(self.die_set, replace)
        dice = Dice(die_set)
        return dice.roll()
        
    def set_one_h_amount(self, value):
        Dice(value).roll()  #Test that the value is valid
        self.one_h_amount = value
        self.save()
        
    def set_two_h_amount(self, value):
        Dice(value).roll()  #Test that the value is valid
        self.two_h_amount = value
        self.save()
        
    def set_ranged_amount(self, value):
        Dice(value).roll()  #Test that the value is valid
        self.ranged_amount = value
        self.save()
        
    def set_shield_amount(self, value):
        Dice(value).roll()  #Test that the value is valid
        self.shield_amount = value
        self.save()
        
    def clone(self, et):
        new = CombatStyle(name=self.name, die_set=self.die_set, enemy_template=et,
                          one_h_amount=self.one_h_amount, two_h_amount=self.two_h_amount,
                          ranged_amount=self.ranged_amount, shield_amount=self.shield_amount)
        new.save()
        for weapon in EnemyWeapon.objects.filter(combat_style=self):
            EnemyWeapon.create(combat_style=new, weapon=weapon.weapon, probability=weapon.probability)
        for weapon in CustomWeapon.objects.filter(combat_style=self):
            cw = CustomWeapon.create(new.id, weapon.type, weapon.name, weapon.probability)
            cw.damage = weapon.damage
            cw.size = weapon.size
            cw.reach = weapon.reach
            cw.ap = weapon.ap
            cw.hp = weapon.hp
            cw.damage_modifier = weapon.damage_modifier
            cw.save()
            
        
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
        
class CustomWeapon(models.Model, Printer):
    combat_style = models.ForeignKey(CombatStyle)
    name = models.CharField(max_length=80)
    probability = models.SmallIntegerField(default=0)
    damage = models.CharField(max_length=30, default=0)
    type = models.CharField(max_length=30, default='1h-melee', choices=(
                                ('1h-melee', '1-h Melee'),
                                ('2h-melee', '2-h Melee'),
                                ('ranged', 'Ranged'),
                                ('shield', 'Shield'),
                            ))
    size = models.CharField(max_length=1, default='M', choices=(
                                            ('S', 'S'),
                                            ('M', 'M'),
                                            ('L', 'L'),
                                            ('H', 'H'),
                                            ('E', 'E'),
                                        ))
    reach = models.CharField(max_length=2, default='M', choices=(
                                        ('-', '-'),
                                        ('T', 'T'),
                                        ('S', 'S'),
                                        ('M', 'M'),
                                        ('L', 'L'),
                                        ('VL', 'VL'),
                                    ))
    ap = models.SmallIntegerField(default=0)
    hp = models.SmallIntegerField(default=0)
    damage_modifier = models.BooleanField(default=False)

    def set_probability(self, value):
        self.probability = value
        self.save()
        if value == 0:
            self.delete()
    
    @classmethod
    def create(cls, cs_id, type, name='Custom weapon', probability=1):
        cs = CombatStyle.objects.get(id=cs_id)
        cw = cls(combat_style=cs, type=type, name=name, probability=probability)
        cw.save()
        return cw
        
class SkillAbstract(models.Model, Printer):
    name = models.CharField(max_length=80)
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
        die_set = replace_die_set(self.die_set, replace)
        dice = Dice(die_set)
        return dice.roll()
        
    def set_value(self, value):
        replace = {'STR': 0, 'SIZ': 0, 'CON': 0, 'INT': 0, 'DEX': 0, 'POW': 0, 'CHA': 0}
        temp_value = replace_die_set(value, replace)
        Dice(temp_value).roll()
        self.die_set = value.upper()
        self.save()
        
class CustomSkill(models.Model, Printer):
    ''' Customs skills on the Enemy Templates '''
    enemy_template = models.ForeignKey(EnemyTemplate)
    name = models.CharField(max_length=80)
    die_set = models.CharField(max_length=30, blank=True)
    include = models.BooleanField()

    def roll(self, replace={}):
        die_set = replace_die_set(self.die_set, replace)
        dice = Dice(die_set)
        return dice.roll()
        
    def set_value(self, value):
        replace = {'STR': 0, 'SIZ': 0, 'CON': 0, 'INT': 0, 'DEX': 0, 'POW': 0, 'CHA': 0}
        temp_value = replace_die_set(value, replace)
        Dice(temp_value).roll()
        self.die_set = value.upper()
        self.save()
        
    @classmethod
    def create(cls, et_id):
        et = EnemyTemplate.objects.get(id=et_id)
        cs = CustomSkill(enemy_template=et, name='Custom skill', include=True)
        cs.save()
        return cs
    
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
        self.armor = value.upper()
        self.save()
        
    @classmethod
    def create(cls, hit_location, enemy_template, armor=None):
        # When creating a new template, armor defaults to race armor
        # When cloning a template, we copy also the armor value
        if armor is None:
            armor = hit_location.armor
        ehl = EnemyHitLocation(hit_location=hit_location,
                               enemy_template=enemy_template,
                               armor=armor)
        ehl.save()
        return ehl
        
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
        self.default_value = value.upper()
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
        self.die_set = value.upper()
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
    name = models.CharField(max_length=80)
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
        self.notes = enemy_template.notes

    def generate(self, suffix=None):
        self.name = self.et.name
        if suffix:
            self.name += ' %s' % suffix
        for stat in self.et.stats:
            self.stats[stat.name] = stat.roll()
            self.stats_list.append({'name': stat.name, 'value': self.stats[stat.name]})
        self._add_skills()
        self._add_spells()
        self._calculate_attributes()
        self._add_hit_locations()
        self._add_combat_styles()
        return self
        
    @property
    def get_stats(self):
        return self.stats_list
        
    def _add_skills(self):
        for skill in self.et.skills:
            if skill.include:
                self.skills.append({'name': skill.name, 'value': skill.roll(self.stats)})
    
    def _add_combat_styles(self):
        for cs in self.et.combat_styles:
            combat_style = {}
            combat_style['value'] = cs.roll(self.stats)
            combat_style['name'] = cs.name
            combat_style['weapons'] = self._add_weapons(cs)
            self.combat_styles.append(combat_style)
            
    def _add_weapons(self, cs):
        ''' Returns a list of weapons based on the given CombatStyle's weapon selections and probabilities
        '''
        output = []
        one_h_amount = min(cs.roll_one_h_amount(), len(cs.one_h_options))
        two_h_amount = min(cs.roll_two_h_amount(), len(cs.two_h_options))
        ranged_amount = min(cs.roll_ranged_amount(), len(cs.ranged_options))
        shield_amount = min(cs.roll_shield_amount(), len(cs.shield_options))
        output.extend(self._get_items(cs.one_h_options, one_h_amount))
        output.extend(self._get_items(cs.two_h_options, two_h_amount))
        output.extend(self._get_items(cs.ranged_options, ranged_amount))
        output.extend(self._get_items(cs.shield_options, shield_amount))
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
        self.attributes['movement'] = self.et.movement
    
    def _calculate_action_points(self):
        dex_int = self.stats['DEX'] + self.stats['INT']
        if dex_int <= 12: self.attributes['action_points'] = 1
        elif dex_int <= 24: self.attributes['action_points'] = 2
        elif dex_int <= 36: self.attributes['action_points'] = 3
        elif dex_int <= 48: self.attributes['action_points'] = 4
        
    def _calculate_damage_modifier(self):
        if self.stats['STR'] == 0 or self.stats['SIZ'] == 0:
            self.attributes['damage_modifier'] = '0'
            return
        DICE_STEPS = ('-1D8', '-1D6', '-1D4', '-1D2', '+0', '+1D2', '+1D4', '+1D6', '+1D8', '+1D10', '+1D12',
                      '+2D6', '+1D8+1D6', '+2D8', '+1D10+1D8', '+2D10', '+2D10+1D2', '+2D10+1D4', '+2D10+1D6')
        str_siz = self.stats['STR'] + self.stats['SIZ']
        if str_siz <= 50:
            index = (str_siz-1) / 5
        else:
            index = ((str_siz - 1 - 50) / 10) + 10
        self.attributes['damage_modifier'] = DICE_STEPS[index]
        
