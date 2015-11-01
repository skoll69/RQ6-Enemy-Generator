from enemygen.models import AdditionalFeatureList
from django.db import models
from django.contrib.auth.models import User
from enemygen.enemygen_lib import replace_die_set, select_random_items
from enemygen.dice import Dice
from taggit.managers import TaggableManager
import ordereddict
from django.db.models import Q

WEAPON_TYPE_CHOICES = (('1h-melee', '1-h Melee'), ('2h-melee', '2-h Melee'), ('ranged', 'Ranged'), ('shield', 'Shield'))
WEAPON_LENGTH_CHOICES = (('-', '-'), ('S', 'S'), ('M', 'M'), ('L', 'L'), ('A', 'A'),)
DAMAGE_BONUS_STEPS = ((12, '-1D6'), (16, '-1D4'), (24, 'None'), (32, '+1D4'), (40, '+1D6'), (56, '+2D6'),
                      (72, '+3D6'), (88, '+4D6'), (104, '+5D6'), (120, '+6D6'), (136, '+7D6'))


class Printer:
    """ A simple class for returning the name of the element """
    def __init__(self):
        self.name = ''  # Not used. Added just to keep Pycharm from complaining.

    def __unicode__(self):
        return self.name


class MWEnemyTemplate(models.Model, Printer):
    name = models.CharField(max_length=50)
    owner = models.ForeignKey(User, related_name='mw_et_owner')
    spell_amount = models.CharField(max_length=30, null=True, blank=True, default='0')
    generated = models.IntegerField(default=0)
    used = models.IntegerField(default=0)
    published = models.BooleanField(default=False)
    rank_choices = ((1, 'Rabble'), (2, 'Novice'), (3, 'Skilled'), (4, 'Veteran'), (5, 'Master'))
    rank = models.SmallIntegerField(max_length=30, default=2, choices=rank_choices)
    movement = models.CharField(max_length=50, default=6)
    notes = models.TextField(default='', null=True, blank=True)
    tags = TaggableManager(blank=True)
    namelist = models.ForeignKey(AdditionalFeatureList, null=True, blank=True, related_name='mw_et_namelist')
    armor = models.CharField(max_length=50, default=0, null=True, blank=True)

    class Meta:
        ordering = ['name', ]
        
    @classmethod
    def create(cls, owner, name="Enemy Template"):
        enemy_template = cls(name=name, owner=owner)
        enemy_template.save()
        enemy_template.name = '%s %s' % (name, enemy_template.id)
        enemy_template.save()
        for stat in StatAbstract.objects.all():
            es = EnemyStat(stat=stat, enemy_template=enemy_template, die_set='3D6')
            es.save()
        enemy_template._create_normal_template()
        return enemy_template
    
    def _create_normal_template(self):
        for skill in SkillAbstract.objects.all():
            es = EnemySkill(skill=skill, enemy_template=self, die_set=skill.default_value, include=skill.include)
            es.save()
        cs = CombatStyle(name="Primary Attack", enemy_template=self)
        cs.save()
        
    def generate(self, suffix=None, increment=False):
        if increment:
            self.generated += 1
            self.save()
        return _Enemy(self).generate(suffix)

    def increment_used(self):
        """ Increments the used-count by one. """
        self.used += 1
        self.save()
        
    def get_tags(self):
        return sorted(list(self.tags.names()))
    
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
    def included_skills(self):
        return EnemySkill.objects.filter(enemy_template=self, include=True)
        
    @property
    def raw_skills(self):
        return EnemySkill.objects.filter(enemy_template=self)
        
    @property
    def included_custom_skills(self):
        return CustomSkill.objects.filter(enemy_template=self, include=True)
        
    @property
    def custom_skills(self):
        return CustomSkill.objects.filter(enemy_template=self)
        
    @property
    def spells(self):
        output = []
        output.extend(list(EnemySpell.objects.filter(enemy_template=self)))
        output.extend(list(CustomSpell.objects.filter(enemy_template=self, probability__gt=0)))
        return output
        
    @property
    def combat_styles(self):
        return CombatStyle.objects.filter(enemy_template=self)
        
    def clone(self, owner):
        name = "Copy of %s" % self.name
        new = MWEnemyTemplate(owner=owner, race=self.race, name=name)
        new.movement = self.movement
        new.rank = self.rank
        new.spell_amount = self.spell_amount
        new.notes = self.notes
        new.namelist = self.namelist
        new.save()
        for tag in self.tags.all():
            new.tags.add(tag)
        for stat in self.stats:
            es = EnemyStat(stat=stat.stat, enemy_template=new, die_set=stat.die_set)
            es.save()
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
        if len(bonus) == 0:
            return
        # Validate bonus
        replace = {'STR': 0, 'SIZ': 0, 'CON': 0, 'INT': 0, 'DEX': 0, 'POW': 0, 'APP': 0}
        temp_value = replace_die_set(bonus, replace)
        Dice(temp_value).roll()
        
        bonus = bonus.upper()

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
            
    def is_starred(self, user):
        if user.is_authenticated():
            try:
                Star.objects.get(user=user, template=self)
                return True
            except Star.DoesNotExist:
                pass
        return False
            
    def toggle_star(self, user):
        Star.create_or_delete(user, self)
        
    @classmethod
    def get_starred(cls, user):
        if user.is_authenticated():
            stars = Star.objects.filter(user=user).order_by('template__rank', 'template__name')
            return [star.template for star in stars]
        else:
            return []
            
    @classmethod
    def search(cls, string, user, rank_filter=None):
        if user.is_authenticated():
            queryset = MWEnemyTemplate.objects.filter(Q(published=True) | Q(published=False, owner=user))
        else:
            queryset = MWEnemyTemplate.objects.filter(published=True)
        if rank_filter:
            queryset = queryset.filter(rank__in=rank_filter)
        if string:
            for word in string.split(' '):
                if word[0] == '-':
                    word = word[1:]
                    queryset = queryset.exclude(name__icontains=word)
                    queryset = queryset.exclude(tags__name__icontains=word)
                else:
                    queryset = queryset.filter(Q(name__icontains=word) | 
                                               Q(tags__name__icontains=word)
                                               )
        return queryset.distinct()
        
    def summary_dict(self, user=None):
        """ Returns summary information about the EnemyTemplate in as a dict so that it can be jsoned """
        output = {'name': self.name, 'rank': self.rank, 'owner': self.owner.username,
                  'tags': self.get_tags(), 'id': self.id}
        if user:
            output['starred'] = self.is_starred(user)
        return output


class MWParty(models.Model, Printer):
    name = models.CharField(max_length=50)
    owner = models.ForeignKey(User, related_name='mw_party_owner')
    published = models.BooleanField(default=False)
    notes = models.TextField(null=True, blank=True, default='')
    tags = TaggableManager(blank=True)
    
    class Meta:
        ordering = ['name', ]
        
    @classmethod
    def create(cls, owner):
        p = cls(name='New Party', owner=owner)
        p.save()
        return p
        
    def add(self, template):
        """ Adds a template to the Party """
        if len(TemplateToParty.objects.filter(template=template, party=self)) == 0:
            ttp = TemplateToParty(template=template, party=self, amount='1')
            ttp.save()
            
    def set_amount(self, template, amount):
        Dice(amount).roll()  # Test that the value is valid
        ttp = TemplateToParty.objects.get(template=template, party=self)
        ttp.amount = amount
        ttp.save()
    
    @property
    def template_specs(self):
        return TemplateToParty.objects.filter(party=self).order_by('template__rank').reverse()
        
    def set_published(self, published):
        self.published = published
        self.save()

    def get_tags(self):
        return sorted(list(self.tags.names()))
        
    def clone(self, owner):
        name = "Copy of %s" % self.name
        new = MWParty(name=name, owner=owner, notes=self.notes)
        new.save()
        for tag in self.tags.all():
            new.tags.add(tag)
        for ttp in self.template_specs:
            new_ttp = TemplateToParty(template=ttp.template, party=new, amount=ttp.amount)
            new_ttp.save()
        return new


class TemplateToParty(models.Model):
    template = models.ForeignKey(MWEnemyTemplate)
    party = models.ForeignKey(MWParty)
    amount = models.CharField(max_length=50)
    
    def get_amount(self):
        return Dice(self.amount).roll()        


class CombatStyle(models.Model):
    enemy_template = models.ForeignKey(MWEnemyTemplate)
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
        
    @property
    def custom_weapons(self):
        return CustomWeapon.objects.filter(combat_style=self)
    
    def roll(self, replace):
        die_set = replace_die_set(self.die_set, replace)
        dice = Dice(die_set)
        return dice.roll()
        
    def set_one_h_amount(self, value):
        Dice(value).roll()  # Test that the value is valid
        self.one_h_amount = value.lower()
        self.save()
        
    def set_two_h_amount(self, value):
        Dice(value).roll()  # Test that the value is valid
        self.two_h_amount = value.lower()
        self.save()
        
    def set_ranged_amount(self, value):
        Dice(value).roll()  # Test that the value is valid
        self.ranged_amount = value.lower()
        self.save()
        
    def set_shield_amount(self, value):
        Dice(value).roll()  # Test that the value is valid
        self.shield_amount = value.lower()
        self.save()
        
    def set_value(self, value):
        replace = {'STR': 0, 'SIZ': 0, 'CON': 0, 'INT': 0, 'DEX': 0, 'POW': 0, 'APP': 0}
        value = value.upper()
        temp_value = replace_die_set(value, replace)
        Dice(temp_value).roll()
        self.die_set = value
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
            cw.reach = weapon.reach
            cw.hp = weapon.hp
            cw.damage_bonus = weapon.damage_bonus
            cw.save()


class Weapon(models.Model, Printer):
    """ Weapons. Created by admins based on rulebooks. """
    name = models.CharField(max_length=80)
    damage = models.CharField(max_length=30, default=0)
    base_skill = models.CharField(max_length=50, default=0)
    type = models.CharField(max_length=30, choices=WEAPON_TYPE_CHOICES)
    length = models.CharField(max_length=2, choices=WEAPON_LENGTH_CHOICES, null=True, blank=True)
    hp = models.SmallIntegerField(default=0)
    damage_bonus = models.CharField(max_length=10, default='full',
                                    choices=(('none', 'None'), ('half', 'Half'), ('full', 'Full'),))
    parry = models.BooleanField(default=True)
    range = models.CharField(max_length=15, null=True, blank=True)

    class Meta:
        ordering = ['name', ]


class EnemyWeapon(models.Model, Printer):
    """ Enemy-specific instance of a Weapon. Links selected weapon to CombatStyle and records
        Probability.
    """
    combat_style = models.ForeignKey(CombatStyle)
    weapon = models.ForeignKey(Weapon)
    probability = models.SmallIntegerField(default=1)
    die_set = models.CharField(max_length=50)
    
    class Meta:
        unique_together = ('combat_style', 'weapon')

    # noinspection PyUnresolvedReferences
    def __getattr__(self, item):
        if item == '_weapon_cache':
            return super(EnemyWeapon, self).__getattr__(item)
        else:
            return self.weapon.__dict__[item]

    def set_probability(self, value):
        self.probability = value
        self.save()
        if value == 0:
            self.delete()
            
    def set_die_set(self, value):
        # Validate die set
        replace = {'STR': 0, 'SIZ': 0, 'CON': 0, 'INT': 0, 'DEX': 0, 'POW': 0, 'APP': 0}
        value = value.upper()
        temp_value = replace_die_set(value, replace)
        Dice(temp_value).roll()
        self.die_set = value
        self.save()

    def roll(self):
        return Dice(self.die_set).roll()

    @classmethod
    def create(cls, combat_style, weapon, probability):
        ew = EnemyWeapon(combat_style=combat_style, weapon=weapon, probability=probability)
        ew.die_set = weapon.base_skill
        ew.save()
        return ew


class CustomWeapon(models.Model, Printer):
    combat_style = models.ForeignKey(CombatStyle)
    name = models.CharField(max_length=80)
    die_set = models.CharField(max_length=50, default=20)
    damage = models.CharField(max_length=30, default=0)
    type = models.CharField(max_length=30, default='1h-melee', choices=WEAPON_TYPE_CHOICES)
    length = models.CharField(max_length=2, default='M', choices=WEAPON_LENGTH_CHOICES)
    hp = models.SmallIntegerField(default=0)
    damage_bonus = models.CharField(max_length=10, default='full',
                                    choices=(('none', 'None'), ('half', 'Half'), ('full', 'Full'),))
    parry = models.BooleanField(default=True)
    range = models.CharField(max_length=15, default='-', null=True, blank=True)
    probability = models.SmallIntegerField(default=0)

    def set_probability(self, value):
        self.probability = value
        self.save()
    
    def set_die_set(self, value):
        # Validate die set
        replace = {'STR': 0, 'SIZ': 0, 'CON': 0, 'INT': 0, 'DEX': 0, 'POW': 0, 'APP': 0}
        value = value.upper()
        temp_value = replace_die_set(value, replace)
        Dice(temp_value).roll()
        self.die_set = value
        self.save()

    def roll(self):
        return Dice(self.die_set).roll()

    @classmethod
    def create(cls, cs_id, weapontype, name='Custom weapon', probability=1):
        cs = CombatStyle.objects.get(id=cs_id)
        cw = cls(combat_style=cs, type=weapontype, name=name, probability=probability)
        cw.save()
        return cw


class SkillAbstract(models.Model, Printer):
    name = models.CharField(max_length=80)
    default_value = models.CharField(max_length=30, blank=True)
    include = models.BooleanField()

    class Meta:
        ordering = ['name', ]


class EnemySkill(models.Model, Printer):
    skill = models.ForeignKey(SkillAbstract)
    enemy_template = models.ForeignKey(MWEnemyTemplate)
    die_set = models.CharField(max_length=100, blank=True)
    include = models.BooleanField()
    
    class Meta:
        ordering = ['skill', ]
        unique_together = ('enemy_template', 'skill')
    
    @property
    def name(self):
        return self.skill.name

    def roll(self, replace=None):
        die_set = replace_die_set(self.die_set, replace)
        dice = Dice(die_set)
        return dice.roll()
        
    def set_value(self, value):
        replace = {'STR': 0, 'SIZ': 0, 'CON': 0, 'INT': 0, 'DEX': 0, 'POW': 0, 'APP': 0}
        temp_value = replace_die_set(value, replace)
        Dice(temp_value).roll()
        self.die_set = value.upper()
        self.save()


class CustomSkill(models.Model, Printer):
    """ Customs skills on the Enemy Templates """
    enemy_template = models.ForeignKey(MWEnemyTemplate)
    name = models.CharField(max_length=80)
    die_set = models.CharField(max_length=30, blank=True)
    include = models.BooleanField()

    def roll(self, replace=None):
        die_set = replace_die_set(self.die_set, replace)
        dice = Dice(die_set)
        return dice.roll()
        
    def set_value(self, value):
        replace = {'STR': 0, 'SIZ': 0, 'CON': 0, 'INT': 0, 'DEX': 0, 'POW': 0, 'APP': 0}
        temp_value = replace_die_set(value, replace)
        Dice(temp_value).roll()
        self.die_set = value.upper()
        self.save()
        
    @classmethod
    def create(cls, et_id):
        et = MWEnemyTemplate.objects.get(id=et_id)
        cs = CustomSkill(enemy_template=et, name='Custom skill', include=True)
        cs.save()
        return cs


class StatAbstract(models.Model, Printer):
    name = models.CharField(max_length=30)
    order = models.SmallIntegerField(null=True)
    
    class Meta:
        ordering = ['order', ]


class EnemyStat(models.Model, Printer):
    stat = models.ForeignKey(StatAbstract)
    enemy_template = models.ForeignKey(MWEnemyTemplate)
    die_set = models.CharField(max_length=30, null=True)
    
    class Meta:
        ordering = ['stat', ]
    
    @property
    def name(self):
        return self.stat.name
        
    def roll(self):
        dice = Dice(self.die_set)
        return dice.roll()

    def set_value(self, value):
        Dice(value).roll()  # Test that the value is valid
        self.die_set = value.lower()
        self.save()


class SpellAbstract(models.Model, Printer):
    """ A Spell. """
    name = models.CharField(max_length=30)
    detail = models.BooleanField(default=False)
    default_detail = models.CharField(max_length=50, null=True, blank=True)
    
    class Meta:
        ordering = ['name', ]


class EnemySpell(models.Model, Printer):
    """ Enemy-specific instance of a SpellAbstract """
    spell = models.ForeignKey(SpellAbstract)
    enemy_template = models.ForeignKey(MWEnemyTemplate)
    probability = models.SmallIntegerField(default=0)
    detail = models.CharField(max_length=50, null=True, blank=True)
        
    class Meta:
        ordering = ['spell', ]
        unique_together = ('spell', 'enemy_template')
    
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
    """ Custom spells created by users """
    enemy_template = models.ForeignKey(MWEnemyTemplate)
    name = models.CharField(max_length=80)
    probability = models.SmallIntegerField(default=0)

    @classmethod
    def create(cls, et_id):
        et = MWEnemyTemplate.objects.get(id=et_id)
        cs = cls(enemy_template=et, name='Custom spell', probability=1)
        cs.save()
        return cs
    
    def set_probability(self, value):
        self.probability = value
        self.save()

    class Meta:
        ordering = ['name', ]


class ChangeLog(models.Model, Printer):
    publish_date = models.DateField()
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=3000)
    
    class Meta:
        ordering = ['publish_date', ]


class _Enemy(object):
    """ Enemy instance created based on an EnemyTemplate. This is the stuff that gets printed
        for the user when Generate is clicked.
    """
    def __init__(self, enemy_template):
        self.name = ''
        self.et = enemy_template
        self.stats = ordereddict.OrderedDict()
        self.stats_list = []
        self.skills = []
        self.skills_dict = {}   # Used during enemy generation
        self.spells = []
        self.template = enemy_template.name
        self.attributes = {}
        self.combat_styles = []
        self.notes = enemy_template.notes

    def generate(self, suffix=None):
        self._generate_name(suffix)
        self._add_stats()
        self._add_skills()
        self._add_spells()
        self._calculate_attributes()
        self._add_combat_styles()
        return self
        
    @property
    def get_stats(self):
        return self.stats_list

    def _generate_name(self, suffix):
        self.name = self.et.name
        if suffix:
            self.name += ' %s' % suffix
        if self.et.namelist:
            self.name = '%s (%s)' % (self.et.namelist.get_random_item(), self.name)
        
    def _add_stats(self):
        for stat in self.et.stats:
            self.stats[stat.name] = stat.roll()
            self.stats_list.append({'name': stat.name, 'value': self.stats[stat.name], 'x5': self.stats[stat.name]*5})

    def _add_skills(self):
        for skill in self.et.skills:
            if skill.include:
                value = skill.roll(self.stats)
                self.skills.append({'name': skill.name, 'value': value})
                self.skills_dict[skill.name] = value
    
    def _add_combat_styles(self):
        for cs in self.et.combat_styles:
            combat_style = {'weapons': self._add_weapons(cs)}
            self.combat_styles.append(combat_style)
            
    def _add_weapons(self, cs):
        """ Returns a list of weapons based on the given CombatStyle's weapon selections and probabilities
        """
        output = []
        one_h_amount = min(cs.roll_one_h_amount(), len(cs.one_h_options))
        two_h_amount = min(cs.roll_two_h_amount(), len(cs.two_h_options))
        ranged_amount = min(cs.roll_ranged_amount(), len(cs.ranged_options))
        shield_amount = min(cs.roll_shield_amount(), len(cs.shield_options))
        output.extend(select_random_items(cs.one_h_options, one_h_amount))
        output.extend(select_random_items(cs.two_h_options, two_h_amount))
        output.extend(select_random_items(cs.ranged_options, ranged_amount))
        output.extend(select_random_items(cs.shield_options, shield_amount))
        return output
        
    def _add_spells(self):
        amount = min(Dice(self.et.spell_amount).roll(), len(self.et.spells))
        self.spells = sorted(select_random_items(self.et.spells, amount), key=lambda s: s.name)

    def _calculate_attributes(self):
        self._calculate_damage_bonus(self.stats['STR'], self.stats['SIZ'])
        self.attributes['magic_points'] = self.stats['POW']
        self.attributes['armor'] = self.et.armor
        self.attributes['movement'] = self.et.movement
        self.attributes['hit_points'] = self.stats['CON'] + self.stats['SIZ']

    def _calculate_damage_bonus(self, strength, siz):
        if strength == 0 or siz == 0:
            self.attributes['damage_bonus'] = '+0'
            return
        str_siz = strength + siz
        for item in DAMAGE_BONUS_STEPS:
            if str_siz <= item[0]:
                self.attributes['damage_bonus'] = item[1]
                return
        self.attributes['damage_bonus'] = '+8D6'


class Star(models.Model):
    """ Functionality for starring templates (marking as favourite) """
    user = models.ForeignKey(User, related_name='mw_star_user')
    template = models.ForeignKey(MWEnemyTemplate)
    
    class Meta:
        unique_together = ('user', 'template')
    
    @classmethod
    def create_or_delete(cls, user, template):
        """ Creates a Star if it doesn't exist, or deletes it if it does """
        try:
            star = Star.objects.get(user=user, template=template)
            star.delete()
        except Star.DoesNotExist:
            star = Star(user=user, template=template)
            star.save()
    
    
def _divide_round_up(n, d):
    return (n + (d - 1))/d
