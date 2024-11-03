# pylint: disable=no-member

from django.db.models import Q
from django.db import models
from django.contrib.auth.models import User

from .enemygen_lib import ValidationError, replace_die_set, select_random_items
from .dice import Dice, clean
from taggit.managers import TaggableManager

from collections import OrderedDict
import random
import math

WEAPON_TYPE_CHOICES = (('1h-melee', '1-h Melee'), ('2h-melee', '2-h Melee'), ('ranged', 'Ranged'), ('shield', 'Shield'))
WEAPON_SIZE_CHOICES = (('S', 'S'), ('M', 'M'), ('L', 'L'), ('H', 'H'), ('E', 'E'), ('C', 'C'))
WEAPON_REACH_CHOICES = (('-', '-'), ('T', 'T'), ('S', 'S'), ('M', 'M'), ('L', 'L'), ('VL', 'VL'), ('U', 'U'))
DICE_STEPS = ('-1d8', '-1d6', '-1d4', '-1d2', '+0', '+1d2', '+1d4', '+1d6', '+1d8', '+1d10', '+1d12',
              '+2d6', '+1d8+1d6', '+2d8', '+1d10+1d8', '+2d10', '+2d10+1d2', '+2d10+1d4', '+2d10+1d6', '+2d10+1d8',
              '+3d10', '+3d10+1d2', '+3d10+1d4', '+3d10+1d6', '+3d10+1d8',
              '+4d10', '+4d10+1d2', '+4d10+1d4', '+4d10+1d6', '+4d10+1d8',
              '+5d10', '+5d10+1d2', '+5d10+1d4', '+5d10+1d6', '+5d10+1d8')


class Ruleset(models.Model):
    """  Ruleset element. Not really utilized currently, as the tools supports only RQ6 """
    name = models.CharField(max_length=30)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    stats = models.ManyToManyField('StatAbstract', blank=True)
    skills = models.ManyToManyField('SkillAbstract', blank=True)
    races = models.ManyToManyField('Race', blank=True)

        
class Weapon(models.Model):
    """ Weapons. Created by admins based on rulebooks. """
    name = models.CharField(max_length=80)
    damage = models.CharField(max_length=30, default=0)
    type = models.CharField(max_length=30, choices=WEAPON_TYPE_CHOICES)
    size = models.CharField(max_length=1, choices=WEAPON_SIZE_CHOICES)
    reach = models.CharField(max_length=2, choices=WEAPON_REACH_CHOICES)
    ap = models.SmallIntegerField(default=0)
    hp = models.SmallIntegerField(default=0)
    damage_modifier = models.BooleanField(default=True)
    special_effects = models.CharField(max_length=300, null=True, blank=True)
    range = models.CharField(max_length=15, null=True, blank=True)
    tags = TaggableManager(blank=True)
        
    class Meta:
        ordering = ['name', ]

        
class Race(models.Model):
    """ Template race. Templates inherit Movement, Hit Locations and notes. Discorporated attribute used by Spirits """
    name = models.CharField(max_length=30)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    movement = models.CharField(max_length=50, default=6)
    special = models.TextField(blank=True)
    published = models.BooleanField(default=False)
    discorporate = models.BooleanField(default=False)
    elemental = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['name', ]

    def __str__(self):
        return self.name

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
        HitLocation(name='Right leg', range_start=1, range_end=3, race=race, hp_modifier=0).save()
        HitLocation(name='Left leg', range_start=4, range_end=6, race=race, hp_modifier=0).save()
        HitLocation(name='Abdomen', range_start=7, range_end=9, race=race, hp_modifier=1).save()
        HitLocation(name='Chest', range_start=10, range_end=12, race=race, hp_modifier=2).save()
        HitLocation(name='Right Arm', range_start=13, range_end=15, race=race, hp_modifier=-1).save()
        HitLocation(name='Left Arm', range_start=16, range_end=18, race=race, hp_modifier=-1).save()
        HitLocation(name='Head', range_start=19, range_end=20, race=race, hp_modifier=0).save()
        return race
        
    def set_published(self, published):
        if not published:
            self.published = published
            self.save()
            return
        # Validate
        ok = True
        if not self.discorporate:
            covered = []
            for hl in self.hit_locations:
                covered.extend(range(hl.range_start, hl.range_end+1))
            for x in range(1, 21):  # Iterate through 1-20
                if x not in covered:
                    ok = False
        if ok:
            self.published = published
            self.save()
        else:
            raise ValidationError
            
    @property
    def templates(self):
        return EnemyTemplate.objects.filter(race=self)

    def clone(self, owner):
        race = Race(name='Copy of %s' % self.name, owner=owner, movement=self.movement, special=self.special)
        race.save()
        for stat in self.stats:
            rs = RaceStat(stat=stat.stat, race=race, default_value=stat.default_value)
            rs.save()
        for loc in self.hit_locations:
            hl = HitLocation(name=loc.name, range_start=loc.range_start, range_end=loc.range_end, 
                             race=race, hp_modifier=loc.hp_modifier, armor=loc.armor)
            hl.save()
        return race


class HitLocation(models.Model):
    name = models.CharField(max_length=30)
    armor = models.CharField(max_length=30, default='0')  # die_set
    range_start = models.SmallIntegerField()
    range_end = models.SmallIntegerField()
    race = models.ForeignKey(Race, on_delete=models.CASCADE)
    hp_modifier = models.CharField(max_length=30, default='0')

    class Meta:
        ordering = ['range_start', ]

    def __str__(self):
        return self.name

    @property
    def range(self):
        if self.range_start == self.range_end:
            return '%02d' % self.range_start
        else:
            return '%02d-%02d' % (int(self.range_start), int(self.range_end))
            
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
        
        # Add the new hitlocation also to any existing templates
        for et in race.templates:
            EnemyHitLocation.create(hl, et)
        
        return hl
        
    def set_armor(self, value):
        if not value:
            value = '0'
        Dice(value).roll()  # Test that the value is valid
        self.armor = value.lower()
        self.save()


class EnemyTemplate(models.Model):
    name = models.CharField(max_length=50)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    ruleset = models.ForeignKey(Ruleset, on_delete=models.CASCADE)
    race = models.ForeignKey(Race, on_delete=models.CASCADE)
    folk_spell_amount = models.CharField(max_length=30, null=True, blank=True, default='0')
    theism_spell_amount = models.CharField(max_length=30, null=True, blank=True, default='0')
    sorcery_spell_amount = models.CharField(max_length=30, null=True, blank=True, default='0')
    mysticism_spell_amount = models.CharField(max_length=30, null=True, blank=True, default='0')
    spirit_amount = models.CharField(max_length=30, null=True, blank=True, default='0')
    cult_amount = models.CharField(max_length=30, null=True, blank=True, default='0')
    generated = models.IntegerField(default=0)
    used = models.IntegerField(default=0)
    published = models.BooleanField(default=False)
    natural_armor = models.BooleanField(default=False)
    rank_choices = ((1, 'Rabble'), (2, 'Novice'), (3, 'Skilled'), (4, 'Veteran'), (5, 'Master'))
    rank = models.SmallIntegerField(default=2, choices=rank_choices)
    movement = models.CharField(max_length=50, default=6)
    notes = models.TextField(null=True, blank=True)
    cult_choices = ((0, 'None'), (1, 'Common'), (2, 'Dedicated'), (3, 'Proven'), (4, 'Overseer'), (5, 'Leader'))
    cult_rank = models.SmallIntegerField(default=0, choices=cult_choices)
    tags = TaggableManager(blank=True)
    namelist = models.ForeignKey('AdditionalFeatureList', on_delete=models.CASCADE, null=True, blank=True)
    weapon_filter = models.CharField(max_length=50, blank=True, null=True)
    
    class Meta:
        ordering = ['name', ]

    def __str__(self):
        return self.name

    @classmethod
    def create(cls, owner, ruleset, race, name="Enemy Template"):
        enemy_template = cls(name=name, owner=owner, ruleset=ruleset, race=race)
        enemy_template.notes = race.special
        enemy_template.movement = race.movement
        enemy_template.save()
        if name == 'Enemy Template':
            enemy_template.name = '%s Template %s' % (race.name, enemy_template.id)
            enemy_template.save()
        for stat in race.stats:
            es = EnemyStat(stat=stat.stat, enemy_template=enemy_template, die_set=stat.default_value)
            es.save()
        if enemy_template.is_spirit:
            enemy_template._create_spirit_template()
        elif enemy_template.is_cult:
            pass
        else:
            enemy_template._create_normal_template()
        return enemy_template
    
    def _create_normal_template(self):
        spirit_skills = ('Spectral Combat', 'Discorporate')
        for skill in self.ruleset.skills.all().exclude(name__in=spirit_skills):
            es = EnemySkill(skill=skill, enemy_template=self, die_set=skill.default_value, include=skill.include)
            es.save()
        for hit_location in self.race.hit_locations:
            EnemyHitLocation.create(hit_location, self)
        cs = CombatStyle(name="Primary Combat Style", enemy_template=self)
        cs.save()
        
    def _create_spirit_template(self):
        skill_names = ('Discorporate', 'Spectral Combat', 'Stealth', 'Willpower', 'Folk Magic', 'Devotion',
                       'Exhort', 'Invocation', 'Shaping', 'Binding', 'Trance')
        for skill in self.ruleset.skills.filter(name__in=skill_names):
            es = EnemySkill(skill=skill, enemy_template=self, die_set=skill.default_value, include=skill.include)
            es.save()
        es = EnemySkill.objects.get(skill__name='Stealth', enemy_template=self)
        es.die_set = 'INT+CHA+50'
        es.save()
        es = EnemySkill.objects.get(skill__name='Willpower', enemy_template=self)
        es.die_set = 'POW+POW+50'
        es.save()
        
    @property
    def get_cult_rank(self):
        theist_ranks = ('None', 'Lay Member', 'Initiate', 'Acolyte', 'Priest', 'High priest')
        if self.is_theist:
            return theist_ranks[int(self.cult_rank)]
        else:
            return self.get_cult_rank_display()
    
    @property
    def is_theist(self):
        if self.is_cult:
            return True
        try:
            return EnemySkill.objects.get(skill__name='Devotion', enemy_template=self).include
        except EnemySkill.DoesNotExist:
            return False
    
    @property
    def is_folk_magician(self):
        if self.is_cult:
            return True
        try:
            return EnemySkill.objects.get(skill__name='Folk Magic', enemy_template=self).include
        except EnemySkill.DoesNotExist:
            return False
    
    @property
    def is_sorcerer(self):
        if self.is_cult:
            return True
        try:
            return EnemySkill.objects.get(skill__name='Shaping', enemy_template=self).include
        except EnemySkill.DoesNotExist:
            return False
    
    @property
    def is_mystic(self):
        if self.is_cult:
            return True
        try:
            return EnemySkill.objects.get(skill__name='Mysticism', enemy_template=self).include
        except EnemySkill.DoesNotExist:
            return False
    
    @property
    def is_animist(self):
        if self.is_cult:
            return True
        try:
            return EnemySkill.objects.get(skill__name='Binding', enemy_template=self).include
        except EnemySkill.DoesNotExist:
            return False
    
    def generate(self, suffix=None, increment=False):
        if increment:
            self.generated += 1
            self.save()
        if self.is_spirit:
            return _Spirit(self).generate(suffix)
        elif self.is_elemental:
            return _Elemental(self).generate(suffix)
        elif self.is_cult:
            return _Cult(self).generate(suffix)
        else:
            return _Enemy(self).generate(suffix)

    def increment_used(self):
        """ Increments the used-count by one. """
        self.used += 1
        self.save()
        
    def get_tags(self):
        return sorted(list(self.tags.names()))
    
    @property
    def stats(self):
        return EnemyStat.objects.filter(enemy_template=self).select_related('stat')

    @property
    def stat_dict(self):
        out = {}
        for stat in EnemyStat.objects.filter(enemy_template=self):
            out[stat.name] = stat.die_set
        return out

    @property
    def skills(self):
        output = []
        output.extend(list(EnemySkill.objects.filter(enemy_template=self).select_related('skill')))
        output.extend(list(CustomSkill.objects.filter(enemy_template=self)))
        output = sorted(output, key=lambda k: k.name)
        return output
        
    @property
    def included_standard_skills(self):
        return EnemySkill.objects.filter(enemy_template=self, skill__standard=True, include=True).select_related('skill')
        
    @property
    def is_spirit(self):
        return self.race.discorporate
        
    @property
    def is_cult(self):
        return self.race.name == 'Cult'
        
    @property
    def is_elemental(self):
        return self.race.elemental
        
    @property
    def raw_skills(self):
        return EnemySkill.objects.filter(enemy_template=self).select_related('skill')
        
    @property
    def standard_skills(self):
        return EnemySkill.objects.filter(enemy_template=self, skill__standard=True).select_related('skill')
        
    @property
    def included_magic_skills(self):
        return EnemySkill.objects.filter(enemy_template=self, skill__standard=False, skill__magic=True, include=True).select_related('skill')
        
    @property
    def magic_skills(self):
        return EnemySkill.objects.filter(enemy_template=self, skill__standard=False, skill__magic=True).select_related('skill')
        
    @property
    def included_professional_skills(self):
        return EnemySkill.objects.filter(enemy_template=self, skill__standard=False, skill__magic=False, include=True).select_related('skill')
        
    @property
    def professional_skills(self):
        return EnemySkill.objects.filter(enemy_template=self, skill__standard=False, skill__magic=False).select_related('skill')
        
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
        output.extend(list(CustomSpell.objects.filter(enemy_template=self, type="folk", probability__gt=0)))
        return output

    @property
    def theism_spells(self):
        output = []
        output.extend(list(EnemySpell.objects.filter(enemy_template=self, spell__type="theism")))
        output.extend(list(CustomSpell.objects.filter(enemy_template=self, type="theism", probability__gt=0)))
        return output

    @property
    def sorcery_spells(self):
        output = []
        output.extend(list(EnemySpell.objects.filter(enemy_template=self, spell__type="sorcery")))
        output.extend(list(CustomSpell.objects.filter(enemy_template=self, type="sorcery", probability__gt=0)))
        return output
        
    @property
    def mysticism_spells(self):
        output = []
        output.extend(list(EnemySpell.objects.filter(enemy_template=self, spell__type="mysticism")))
        output.extend(list(CustomSpell.objects.filter(enemy_template=self, type="mysticism", probability__gt=0)))
        return output
        
    @property
    def spirits(self):
        return EnemySpirit.objects.filter(enemy_template=self)

    @property
    def cults(self):
        return EnemyCult.objects.filter(enemy_template=self)

    @property
    def hit_locations(self):
        return EnemyHitLocation.objects.filter(enemy_template=self).select_related('hit_location')

    @property
    def combat_styles(self):
        return CombatStyle.objects.filter(enemy_template=self)
        
    @property
    def additional_features(self):
        return EnemyAdditionalFeatureList.objects.filter(enemy_template=self).select_related('feature_list')
        
    @property
    def nonrandom_features(self):
        return EnemyNonrandomFeature.objects.filter(enemy_template=self)
        
    def add_additional_feature(self, feature_list_id):
        EnemyAdditionalFeatureList.create(enemy_template=self, feature_list_id=feature_list_id)
        
    def add_nonrandom_feature(self, feature_id):
        EnemyNonrandomFeature.create(enemy_template=self, feature_id=feature_id)
        
    def clone(self, owner):
        name = "Copy of %s" % self.name
        new = EnemyTemplate(owner=owner, ruleset=self.ruleset, race=self.race, name=name)
        new.movement = self.movement
        new.rank = self.rank
        new.folk_spell_amount = self.folk_spell_amount
        new.theism_spell_amount = self.theism_spell_amount
        new.sorcery_spell_amount = self.sorcery_spell_amount
        new.mysticism_spell_amount = self.mysticism_spell_amount
        new.spirit_amount = self.spirit_amount
        new.cult_amount = self.cult_amount
        new.notes = self.notes
        new.cult_rank = self.cult_rank
        new.namelist = self.namelist
        new.natural_armor = self.natural_armor
        new.save()
        for tag in self.tags.all():
            new.tags.add(tag)
        for stat in self.stats:
            es = EnemyStat(stat=stat.stat, enemy_template=new, die_set=stat.die_set)
            es.save()
        for hl in self.hit_locations:
            EnemyHitLocation.create(hl.hit_location, enemy_template=new, armor=hl.armor)
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
        for spirit in EnemySpirit.objects.filter(enemy_template=self):
            es = EnemySpirit(enemy_template=new, spirit=spirit.spirit, probability=spirit.probability)
            es.save()
        for cult in EnemyCult.objects.filter(enemy_template=self):
            es = EnemyCult(enemy_template=new, cult=cult.cult, probability=cult.probability)
            es.save()
        for af in self.additional_features:
            EnemyAdditionalFeatureList.create(new, af.feature_list.id, af.probability)
        for nrf in self.nonrandom_features:
            EnemyNonrandomFeature.create(new, nrf.feature.id)
        return new

    def apply_skill_bonus(self, bonus):
        if len(bonus) == 0:
            return
        # Validate bonus
        replace = {'STR': 0, 'SIZ': 0, 'CON': 0, 'INT': 0, 'DEX': 0, 'POW': 0, 'CHA': 0}
        temp_value = replace_die_set(bonus, replace)
        Dice(temp_value).roll()
        
        bonus = bonus.upper()

        if bonus[0] != '+':
            bonus = '+' + bonus
            
        for skill in self.raw_skills:
            skill.set_value(skill.die_set + bonus)
        for skill in self.custom_skills:
            skill.set_value(skill.die_set + bonus)
        for combat_style in self.combat_styles:
            combat_style.set_value(combat_style.die_set + bonus)

    def is_starred(self, user):
        if user.is_authenticated:
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
        if user.is_authenticated:
            stars = Star.objects.filter(user=user).order_by('template__rank', 'template__name')
            return [star.template for star in stars]
        else:
            return []

    @classmethod
    def search(cls, string, user, rank_filter=None, cult_rank_filter=None):
        string = string.strip()
        if user.is_authenticated:
            queryset = EnemyTemplate.objects.filter(Q(published=True) | Q(published=False, owner=user)).select_related('owner', 'race')
        else:
            queryset = EnemyTemplate.objects.filter(published=True).select_related('owner', 'race')
        queryset = queryset.exclude(race__name='Cult')
        if rank_filter:
            queryset = queryset.filter(rank__in=rank_filter)
        if cult_rank_filter:
            queryset = queryset.filter(cult_rank__in=cult_rank_filter)
        if string:
            for word in string.split(' '):
                if word[0] == '-':
                    word = word[1:]
                    queryset = queryset.exclude(name__icontains=word)
                    queryset = queryset.exclude(race__name__icontains=word)
                    queryset = queryset.exclude(tags__name__icontains=word)
                else:
                    queryset = queryset.filter(Q(name__icontains=word) | 
                                               Q(race__name__icontains=word) |
                                               Q(tags__name__icontains=word)
                                               )
        return queryset.distinct()
        
    def summary_dict(self, user=None):
        """ Returns summary information about the EnemyTemplate in as a dict so that it can be jsoned """
        output = {'name': self.name, 'race': self.race.name, 'rank': self.rank, 'owner': self.owner.username,
                  'tags': self.get_tags(), 'id': self.id}
        if user:
            output['starred'] = self.is_starred(user)
        return output


class Party(models.Model):
    name = models.CharField(max_length=50)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
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
        if not published:
            self.published = published
            self.save()
            return
        # Add validation
        ok = True
        if ok:
            self.published = published
            self.save()
        else:
            raise ValidationError
            
    def get_tags(self):
        return sorted(list(self.tags.names()))
        
    def add_additional_feature(self, feature_list_id):
        PartyAdditionalFeatureList.create(party=self, feature_list_id=feature_list_id)
        
    @property
    def additional_features(self):
        return PartyAdditionalFeatureList.objects.filter(party=self)
        
    @property
    def nonrandom_features(self):
        return PartyNonrandomFeature.objects.filter(party=self)
        
    def get_random_additional_features(self):
        features = []
        for feature in self.additional_features:
            if feature.random_has_feature() and len(feature.items) > 0:
                features.append(feature.get_random_item())
        return features

    def add_nonrandom_feature(self, feature_id):
        PartyNonrandomFeature.create(party=self, feature_id=feature_id)
        
    def clone(self, owner):
        name = "Copy of %s" % self.name
        new = Party(name=name, owner=owner, notes=self.notes)
        new.save()
        for tag in self.tags.all():
            new.tags.add(tag)
        for af in self.additional_features:
            new.add_additional_feature(af.feature_list.id)
        for ttp in self.template_specs:
            new_ttp = TemplateToParty(template=ttp.template, party=new, amount=ttp.amount)
            new_ttp.save()
        for nrf in self.nonrandom_features:
            PartyNonrandomFeature.create(new, nrf.feature.id)
        return new


class TemplateToParty(models.Model):
    template = models.ForeignKey(EnemyTemplate, on_delete=models.CASCADE)
    party = models.ForeignKey(Party, on_delete=models.CASCADE)
    amount = models.CharField(max_length=50)
    
    def get_amount(self):
        return Dice(self.amount).roll()

    def __str__(self):
        return self.party.name + ' - ' + self.template.name
    

class CombatStyle(models.Model):
    name = models.CharField(max_length=80)
    die_set = models.CharField(max_length=30, default="STR+DEX")
    enemy_template = models.ForeignKey(EnemyTemplate, on_delete=models.CASCADE)
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
        replace = {'STR': 0, 'SIZ': 0, 'CON': 0, 'INT': 0, 'DEX': 0, 'POW': 0, 'CHA': 0}
        value = clean(value)
        temp_value = replace_die_set(value, replace)
        Dice(temp_value).roll()
        self.die_set = value
        self.save()
        return value
        
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
            cw.special_effects = weapon.special_effects
            cw.natural_weapon = weapon.natural_weapon
            cw.ap_hp_as_per = weapon.ap_hp_as_per
            cw.save()


class EnemyWeapon(models.Model):
    """ Enemy-specific instance of a Weapon. Links selected weapon to CombatStyle and records
        Probability.
    """
    combat_style = models.ForeignKey(CombatStyle, on_delete=models.CASCADE)
    weapon = models.ForeignKey(Weapon, on_delete=models.CASCADE)
    probability = models.SmallIntegerField(default=1)
    
    class Meta:
        unique_together = ('combat_style', 'weapon')
    
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
    def range(self):
        return self.weapon.range
        
    @property
    def ap(self):
        return self.weapon.ap
        
    @property
    def hp(self):
        return self.weapon.hp
        
    @property
    def special_effects(self):
        return self.weapon.special_effects if self.weapon.special_effects else ''
        
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

    def __lt__(self, other):
        return self.name < other.name


class CustomWeapon(models.Model):
    combat_style = models.ForeignKey(CombatStyle, on_delete=models.CASCADE)
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
                                            ('-', '-'),
                                            ('S', 'S'),
                                            ('M', 'M'),
                                            ('L', 'L'),
                                            ('H', 'H'),
                                            ('E', 'E'),
                                            ('C', 'C'),
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
    damage_modifier = models.BooleanField(default=True)
    natural_weapon = models.BooleanField(default=False)
    ap_hp_as_per = models.CharField(max_length=30, default='', null=True, blank=True)
    special_effects = models.CharField(max_length=300, null=True, blank=True)
    range = models.CharField(max_length=15, default='-', null=True, blank=True)

    def set_probability(self, value):
        self.probability = value
        self.save()
    
    @classmethod
    def create(cls, cs_id, weapontype, name='Custom weapon', probability=1):
        cs = CombatStyle.objects.get(id=cs_id)
        cw = cls(combat_style=cs, type=weapontype, name=name, probability=probability)
        cw.save()
        return cw


class SkillAbstract(models.Model):
    name = models.CharField(max_length=80)
    standard = models.BooleanField(default=True)
    magic = models.BooleanField(default=False)
    default_value = models.CharField(max_length=30, blank=True)
    include = models.BooleanField()

    class Meta:
        ordering = ['name', ]

    def __str__(self):
        return self.name


class EnemySkill(models.Model):
    skill = models.ForeignKey(SkillAbstract, on_delete=models.CASCADE)
    enemy_template = models.ForeignKey(EnemyTemplate, on_delete=models.CASCADE)
    die_set = models.CharField(max_length=100, blank=True)
    include = models.BooleanField()
    
    class Meta:
        ordering = ['skill', ]
        unique_together = ('enemy_template', 'skill')
    
    @property
    def name(self):
        return self.skill.name

    def roll(self, replace=None):
        # Ensure, that all valid stats are present in the dict. Some races miss some stats
        # which will cause the generation to crash if the stat is nonetheless used in skills
        replace_full = {'STR': 0, 'SIZ': 0, 'CON': 0, 'INT': 0, 'DEX': 0, 'POW': 0, 'CHA': 0}
        if replace:
            replace_full.update(replace)
        die_set = replace_die_set(self.die_set, replace_full)
        dice = Dice(die_set)
        return dice.roll()
        
    def set_value(self, value):
        replace = {'STR': 0, 'SIZ': 0, 'CON': 0, 'INT': 0, 'DEX': 0, 'POW': 0, 'CHA': 0}
        value = clean(value)
        temp_value = replace_die_set(value, replace)
        Dice(temp_value).roll()
        self.die_set = value
        self.save()
        return value


class CustomSkill(models.Model):
    """ Customs skills on the Enemy Templates """
    enemy_template = models.ForeignKey(EnemyTemplate, on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    die_set = models.CharField(max_length=30, blank=True)
    include = models.BooleanField()

    def __str__(self):
        return self.name

    def roll(self, replace=None):
        die_set = replace_die_set(self.die_set, replace)
        dice = Dice(die_set)
        return dice.roll()
        
    def set_value(self, value):
        replace = {'STR': 0, 'SIZ': 0, 'CON': 0, 'INT': 0, 'DEX': 0, 'POW': 0, 'CHA': 0}
        value = clean(value)
        temp_value = replace_die_set(value, replace)
        Dice(temp_value).roll()
        self.die_set = value
        self.save()
        return value
        
    @classmethod
    def create(cls, et_id):
        et = EnemyTemplate.objects.get(id=et_id)
        cs = CustomSkill(enemy_template=et, name='Custom skill', include=True)
        cs.save()
        return cs


class EnemyHitLocation(models.Model):
    hit_location = models.ForeignKey(HitLocation, on_delete=models.CASCADE)
    enemy_template = models.ForeignKey(EnemyTemplate, on_delete=models.CASCADE)
    armor = models.CharField(max_length=30, blank=True)  # die_set
    
    class Meta:
        ordering = ['hit_location', ]
    
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
        Dice(value).roll()  # Test that the value is valid
        self.armor = value.lower()
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


class StatAbstract(models.Model):
    name = models.CharField(max_length=30)
    order = models.SmallIntegerField(null=True)
    
    class Meta:
        ordering = ['order', ]

    def __str__(self):
        return self.name


class RaceStat(models.Model):
    stat = models.ForeignKey(StatAbstract, on_delete=models.CASCADE)
    race = models.ForeignKey(Race, on_delete=models.CASCADE)
    default_value = models.CharField(max_length=30, null=True)
    
    class Meta:
        ordering = ['stat', ]

    @property
    def name(self):
        return self.stat.name
        
    def set_value(self, value):
        # Test that the value is valid
        Dice(value).roll()
        self.default_value = value.lower()
        self.save()


class EnemyStat(models.Model):
    stat = models.ForeignKey(StatAbstract, on_delete=models.CASCADE)
    enemy_template = models.ForeignKey(EnemyTemplate, on_delete=models.CASCADE)
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


class SpellAbstract(models.Model):
    """ A Spell. """
    name = models.CharField(max_length=30)
    
    choices = (
                ('folk', 'Folk magic'),
                ('theism', 'Theism'),
                ('sorcery', 'Sorcery'),
                ('mysticism', 'Mysticism'),
                )
    type = models.CharField(max_length=30, choices=choices)
    detail = models.BooleanField(default=False)
    default_detail = models.CharField(max_length=50, null=True, blank=True)
    
    class Meta:
        ordering = ['name', ]

    def __str__(self):
        return self.name


class EnemySpell(models.Model):
    """ Enemy-specific instance of a SpellAbstract """
    spell = models.ForeignKey(SpellAbstract, on_delete=models.CASCADE)
    enemy_template = models.ForeignKey(EnemyTemplate, on_delete=models.CASCADE)
    probability = models.SmallIntegerField(default=0)
    detail = models.CharField(max_length=50, null=True, blank=True)
        
    class Meta:
        ordering = ['spell', ]
        unique_together = ('spell', 'enemy_template')
    
    def __str__(self):
        return self.name

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


class CustomSpell(models.Model):
    """ Custom spells created by users """
    enemy_template = models.ForeignKey(EnemyTemplate, on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    probability = models.SmallIntegerField(default=0)
    type = models.CharField(max_length=30, choices=(('folk', 'Folk magic'),
                                                    ('theism', 'Theism'),
                                                    ('sorcery', 'Sorcery'),
                                                    ('mysticism', 'Mysticism'),
                                                    ))

    def __str__(self):
        return self.name

    @classmethod
    def create(cls, et_id, spelltype):
        et = EnemyTemplate.objects.get(id=et_id)
        cs = cls(enemy_template=et, type=spelltype, name='Custom spell', probability=1)
        cs.save()
        return cs
    
    def set_probability(self, value):
        self.probability = value
        self.save()

    class Meta:
        ordering = ['name', ]


class EnemySpirit(models.Model):
    """ Links spirits (EnemyTemplates) to animists """
    enemy_template = models.ForeignKey(EnemyTemplate, on_delete=models.CASCADE, related_name='animist')   # The animist
    spirit = models.ForeignKey(EnemyTemplate, on_delete=models.CASCADE, related_name='spirit')
    probability = models.SmallIntegerField(default=0)
    
    class Meta:
        ordering = ['spirit', ]

    def __str__(self):
        return self.name

    @property
    def name(self):
        return self.spirit.name
        
    @classmethod
    def create(cls, spirit_id, et_id):
        et = EnemyTemplate.objects.get(id=et_id)
        spirit = EnemyTemplate.objects.get(id=spirit_id)
        es = EnemySpirit(enemy_template=et, spirit=spirit, probability=1)
        es.save()
        return es


class EnemyCult(models.Model):
    """ Links Cults to EnemyTemplates """
    enemy_template = models.ForeignKey(EnemyTemplate, on_delete=models.CASCADE, related_name='enemytemplate')
    cult = models.ForeignKey(EnemyTemplate, on_delete=models.CASCADE, related_name='cult')
    probability = models.SmallIntegerField(default=0)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['cult', ]
        
    @property
    def name(self):
        return self.cult.name
        
    @classmethod
    def create(cls, cult_id, et_id):
        et = EnemyTemplate.objects.get(id=et_id)
        cult = EnemyTemplate.objects.get(id=cult_id)
        ec = EnemyCult(enemy_template=et, cult=cult, probability=10)
        ec.save()
        return ec


class AdditionalFeatureList(models.Model):
    name = models.CharField(max_length=80)
    type_choices = (('enemy_feature', 'Enemy feature'), ('party_feature', 'Party feature'), ('name', 'Name'))
    type = models.CharField(max_length=20, choices=type_choices)
    
    class Meta:
        ordering = ['type', 'name']

    def __str__(self):
        return self.name

    @property
    def items(self):
        return AdditionalFeatureItem.objects.filter(feature_list=self)
        
    def get_random_item(self):
        num_items = len(self.items)
        index = random.randint(0, num_items-1)
        return self.items[index]
    
    def __unicode__(self):
        return '%s - %s' % (self.get_type_display(), self.name)


class AdditionalFeatureItem(models.Model):
    name = models.CharField(max_length=1000)
    feature_list = models.ForeignKey(AdditionalFeatureList, on_delete=models.CASCADE)
 
    class Meta:
        ordering = ['name', ]


class EnemyAdditionalFeatureList(models.Model):
    probability = models.CharField(max_length=30, default='POW+POW', null=True, blank=True)
    feature_list = models.ForeignKey(AdditionalFeatureList, on_delete=models.CASCADE)
    enemy_template = models.ForeignKey(EnemyTemplate, on_delete=models.CASCADE)

    class Meta:
        ordering = ['feature_list', ]
    
    @classmethod
    def create(cls, enemy_template, feature_list_id, probability='POW+POW'):
        feature_list = AdditionalFeatureList.objects.get(id=feature_list_id)
        afl = cls(enemy_template=enemy_template, feature_list=feature_list, probability=probability)
        afl.save()
        return afl
    
    @property
    def items(self):
        return self.feature_list.items
        
    @property
    def name(self):
        return self.feature_list.name
        
    def get_random_item(self):
        return self.feature_list.get_random_item()
        
    def random_has_feature(self, replace=None):
        """ Determines randomly whether the enemy has the additional feature or not """
        prob = replace_die_set(self.probability, replace)
        prob = Dice(prob).roll()
        roll = random.randint(1, 100)
        return roll <= prob
        
    def set_probability(self, value):
        if not value:
            value = '0'
        replace = {'STR': 0, 'SIZ': 0, 'CON': 0, 'INT': 0, 'DEX': 0, 'POW': 0, 'CHA': 0}
        temp_value = replace_die_set(value, replace)
        Dice(temp_value).roll()
        self.probability = value.upper()
        self.save()
        
    def __unicode__(self):
        return '%s(%s) - %s' % (self.enemy_template.name, self.enemy_template.id, self.feature_list.name)


class EnemyNonrandomFeature(models.Model):
    enemy_template = models.ForeignKey(EnemyTemplate, on_delete=models.CASCADE)
    feature = models.ForeignKey(AdditionalFeatureItem, on_delete=models.CASCADE)

    def __str__(self):
        return self.enemy_template.name + ' - ' + self.feature.name

    @classmethod
    def create(cls, enemy_template, feature_id):
        feature = AdditionalFeatureItem.objects.get(id=feature_id)
        nonrandom_feature = cls(enemy_template=enemy_template, feature=feature)
        nonrandom_feature.save()
        return nonrandom_feature
        
    def __unicode__(self):
        feature_name = self.feature.name[:40]+'...' if len(self.feature.name) > 43 else self.feature.name
        return '%s(%s) - %s' % (self.enemy_template.name, self.enemy_template.id, feature_name)


class PartyNonrandomFeature(models.Model):
    party = models.ForeignKey(Party, on_delete=models.CASCADE)
    feature = models.ForeignKey(AdditionalFeatureItem, on_delete=models.CASCADE)

    @classmethod
    def create(cls, party, feature_id):
        feature = AdditionalFeatureItem.objects.get(id=feature_id)
        nonrandom_feature = cls(party=party, feature=feature)
        nonrandom_feature.save()
        return nonrandom_feature


class PartyAdditionalFeatureList(models.Model):
    probability = models.CharField(max_length=30, default='50', null=True, blank=True)
    feature_list = models.ForeignKey(AdditionalFeatureList, on_delete=models.CASCADE)
    party = models.ForeignKey(Party, on_delete=models.CASCADE)
    
    class Meta:
        ordering = ['feature_list', ]

    def __str__(self):
        return self.party.name + ' - ' + self.feature_list.name

    @classmethod
    def create(cls, party, feature_list_id):
        feature_list = AdditionalFeatureList.objects.get(id=feature_list_id)
        afl = cls(party=party, feature_list=feature_list)
        afl.save()
        return afl
    
    @property
    def items(self):
        return self.feature_list.items
        
    @property
    def name(self):
        return self.feature_list.name
        
    def get_random_item(self):
        return self.feature_list.get_random_item()
        
    def random_has_feature(self):
        """ Determines randomly whether the enemy has the additional feature or not """
        prob = int(self.probability)
        roll = random.randint(1, 100)
        return roll <= prob
        
    def set_probability(self, value):
        if not value:
            value = '0'
        int(value)  # Test that it's an int-string.
        self.probability = value
        self.save()


class ChangeLog(models.Model):
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
        self.cult_rank = self.et.get_cult_rank
        self.stats = OrderedDict()
        self.stats_list = []
        self.skills = []
        self.skills_dict = {}   # Used during enemy generation
        self.folk_spells = []
        self.theism_spells = []
        self.sorcery_spells = []
        self.mysticism_spells = []
        self.spirits = []
        self.cults = []
        self.hit_locations = []
        self.template = enemy_template.name
        self.attributes = {}
        self.combat_styles = []
        self.additional_features = []
        self.notes = enemy_template.notes
        self.is_theist = False
        self.is_sorcerer = False
        self.is_animist = False
        self.is_mystic = False
        self.is_spirit = self.et.is_spirit

    def generate(self, suffix=None):
        self._generate_name(suffix)
        self._add_stats()
        self._add_skills()
        self._add_spells()
        self._add_additional_features()
        self._add_hit_locations()
        self._calculate_attributes()
        if self.is_animist:
            self._add_spirits()
        if self.et.cult_amount:
            self._add_cults()
        self._add_combat_styles()
        self.natural_armor = self.et.natural_armor
        return self
        
    @property
    def get_stats(self):
        return self.stats_list

    def _generate_name(self, suffix):
        self.name = self.et.name
        if suffix:
            self.name += ' %s' % suffix
        if self.et.namelist:
            self.name = '%s (%s)' % (self.et.namelist.get_random_item().name, self.name)
        
    def _add_stats(self):
        for stat in self.et.stats:
            self.stats[stat.name] = stat.roll()
            self.stats_list.append({'name': stat.name, 'value': self.stats[stat.name]})
    
    def _add_skills(self):
        for skill in self.et.skills:
            if skill.include:
                value = skill.roll(self.stats)
                self.skills.append({'name': skill.name, 'value': value})
                self.skills_dict[skill.name] = value
    
    def _add_combat_styles(self):
        for cs in self.et.combat_styles:
            combat_style = {'value': cs.roll(self.stats), 'name': cs.name, 'weapons': self._add_weapons(cs)}
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
        output = self._adjust_size_and_reach(output)
        return output
        
    def _adjust_size_and_reach(self, weapons):
        """ Adjusts weapon size and reach of big creatures """
        step = (self.stats['SIZ']-11) // 10    # SIZ 21-30: step 1; 31-40: step 2, etc.
        if step == 0:
            return weapons
        sizes = [value for value, _ in WEAPON_SIZE_CHOICES]
        reaches = [value for value, _ in WEAPON_REACH_CHOICES]
        for item in weapons:
            if item.__class__.__name__ == 'EnemyWeapon':
                index = sizes.index(item.weapon.size) + step
                if index < 0:
                    item.weapon.size = 'S'
                else:
                    try:
                        item.weapon.size = sizes[index]
                    except IndexError:
                        item.weapon.size = 'C'

                index = reaches.index(item.weapon.reach) + step
                if index < 1:
                    item.weapon.reach = 'T'
                else:
                    try:
                        item.weapon.reach = reaches[index]
                    except IndexError:
                        item.weapon.reach = 'U'
        return weapons
    
    def _add_hit_locations(self):
        con_siz = self.stats['CON'] + self.stats['SIZ']
        base_hp = ((con_siz-1) // 5) + 1  # used by Head and Legs
        for hl in self.et.hit_locations:
            hp = max(base_hp + Dice(hl.hp_modifier).roll(), 1)
            ap = hl.roll()
            enemy_hl = {'name': hl.name, 'range': hl.range, 'hp': hp, 'ap': ap, 'parent': hl}
            self.hit_locations.append(enemy_hl)
        
    def _add_spells(self):
        amount = min(Dice(self.et.folk_spell_amount).roll(), len(self.et.folk_spells))
        self.folk_spells = sorted(select_random_items(self.et.folk_spells, amount), key=lambda s: s.name)
        amount = min(Dice(self.et.theism_spell_amount).roll(), len(self.et.theism_spells))
        self.theism_spells = sorted(select_random_items(self.et.theism_spells, amount), key=lambda s: s.name)
        amount = min(Dice(self.et.sorcery_spell_amount).roll(), len(self.et.sorcery_spells))
        self.sorcery_spells = sorted(select_random_items(self.et.sorcery_spells, amount), key=lambda s: s.name)
        amount = min(Dice(self.et.mysticism_spell_amount).roll(), len(self.et.mysticism_spells))
        self.mysticism_spells = sorted(select_random_items(self.et.mysticism_spells, amount), key=lambda s: s.name)
        
    def _add_spirits(self):
        spirit_options = self.et.spirits.filter(probability__gt=0).exclude(spirit__race__name='Cult')
        amount = min(Dice(self.et.spirit_amount).roll(), len(spirit_options))
        spirit_templates = select_random_items(spirit_options, amount)
        retries = 5
        for st in spirit_templates:
            i = 0
            spirit = None
            while spirit is None or (spirit.stats['POW'] > self.attributes['max_pow'] and i < retries):
                i += 1
                spirit = st.spirit.generate()
            if spirit.stats['POW'] <= self.attributes['max_pow']:
                self.spirits.append(spirit)
        
    def _add_cults(self):
        amount = min(Dice(self.et.cult_amount).roll(), len(self.et.cults.filter(probability__gt=0)))
        cult_templates = select_random_items(self.et.cults.filter(probability__gt=0), amount)
        for ct in cult_templates:
            self.cult = ct.cult
            cult = ct.cult.generate()
            self.folk_spells += cult.folk_spells
            self.theism_spells += cult.theism_spells
            self.sorcery_spells += cult.sorcery_spells
            self.mysticism_spells += cult.mysticism_spells
            self.spirits += cult.spirits
            self.cults.append(cult)
            
        seen = set()
        self.folk_spells = [x for x in self.folk_spells if x.name not in seen and not seen.add(x.name)]
        seen = set()
        self.theism_spells = [x for x in self.theism_spells if x.name not in seen and not seen.add(x.name)]
        seen = set()
        self.sorcery_spells = [x for x in self.sorcery_spells if x.name not in seen and not seen.add(x.name)]
        seen = set()
        self.mysticism_spells = [x for x in self.mysticism_spells if x.name not in seen and not seen.add(x.name)]
            
        self.folk_spells.sort(key=lambda item: item.name)
        self.theism_spells.sort(key=lambda item: item.name)
        self.sorcery_spells.sort(key=lambda item: item.name)
        self.mysticism_spells.sort(key=lambda item: item.name)
        self.spirits.sort(key=lambda item: item.name)
        
    def _add_additional_features(self):
        for feature_list in self.et.additional_features:
            if feature_list.random_has_feature(self.stats) and len(feature_list.items) > 0:
                feature = feature_list.get_random_item()
                self.additional_features.append(feature)
        for feature in self.et.nonrandom_features:
            fture = feature.feature
            # Used in the html template to show the non-random features only once if there's only one type of enemies
            fture.non_random = True
            self.additional_features.append(fture)
        self.additional_features.sort(key=lambda item: item.feature_list.name)
        
    def _calculate_attributes(self):
        sr_natural = (self.stats['INT'] + self.stats['DEX']) // 2
        sr = sr_natural - self._sr_penalty()
        self._calculate_action_points()
        self._calculate_damage_modifier(self.stats['STR'], self.stats['SIZ'])
        self.attributes['magic_points'] = self.stats['POW']
        self.attributes['strike_rank'] = '%s(%s-%s)' % (sr, sr_natural, self._sr_penalty())
        self.attributes['movement'] = self.et.movement
        if 'Devotion' in self.skills_dict:
            self.is_theist = True
            self.attributes['devotional_pool'] = self._get_devotional_pool()
            self.attributes['max_intensity'] = int(math.ceil(self.skills_dict['Devotion'] / 10))
        if 'Shaping' in self.skills_dict:
            self.is_sorcerer = True
            self.attributes['max_shaping'] = int(math.ceil(self.skills_dict['Shaping'] / 10))
        if 'Invocation' in self.skills_dict:
            self.attributes['intensity'] = int(math.ceil(self.skills_dict['Invocation'] / 10))
        if 'Mysticism' in self.skills_dict and 'Meditation' in self.skills_dict:
            self.is_mystic = True
            self.attributes['max_mysticism_intensity'] = int(math.ceil(self.skills_dict['Mysticism'] / 20))
            self.attributes['max_total_intensity'] = int(math.ceil(self.skills_dict['Meditation'] / 10))
        if 'Binding' in self.skills_dict:
            self.is_animist = True
            self.attributes['max_pow'] = int(math.ceil(self.skills_dict['Binding'] / 10)) * 3
            self.attributes['max_spirits'] = self._get_max_spirits()
            
    def _get_max_spirits(self):
        """ Calculates and returns the maximun number of spirits the animist can control. """
        mult_options = [0, 0.25, 0.5, 0.75, 1, 1]
        spirit_multiplier = mult_options[self.et.cult_rank]
        return int(math.ceil(self.stats['CHA'] * spirit_multiplier))
            
    def _get_devotional_pool(self):
        mult_options = [0, 0, 0.25, 0.5, 0.75, 1]
        devpool_multiplier = mult_options[self.et.cult_rank]
        return int(math.ceil(self.stats['POW'] * devpool_multiplier))
        
    def _sr_penalty(self):
        if self.et.natural_armor:
            return 0
        enc = 0
        for hl in self.hit_locations:
            ap = hl['ap']
            # Disregard armor of the race, which is assumed to be natural
            ap -= int(hl['parent'].hit_location.armor)
            if ap == 1:
                enc += 2
            elif ap > 1:
                enc += ap-1
        return _divide_round_up(enc, 5)
    
    def _calculate_action_points(self):
        self.attributes['action_points'] = int(math.ceil((self.stats['DEX'] + self.stats['INT']) / 12))

    def _calculate_damage_modifier(self, strength, siz):
        if strength == 0 or siz == 0:
            self.attributes['damage_modifier'] = '+0'
            return
        str_siz = strength + siz
        if str_siz <= 50:
            index = (str_siz-1) // 5
        else:
            index = ((str_siz - 1 - 50) // 10) + 10
        try:
            self.attributes['damage_modifier'] = DICE_STEPS[index]
        except IndexError:
            self.attributes['damage_modifier'] = '+6d10'


class _Cult(_Enemy):
    def __init__(self, enemy_template):
        super(_Cult, self).__init__(enemy_template)
        
    def generate(self, suffix=None):
        self._generate_name(suffix)
        self._add_spells()
        self._add_spirits()
        return self
        
    def _add_spirits(self):
        amount = min(Dice(self.et.spirit_amount).roll(), len(self.et.spirits.filter(probability__gt=0)))
        spirit_templates = select_random_items(self.et.spirits.filter(probability__gt=0), amount)
        for st in spirit_templates:
            spirit = st.spirit.generate()
            self.spirits.append(spirit)


class _Spirit(_Enemy):
    """ Spirit type of Enemy """
    def generate(self, suffix=None):
        self._generate_name(suffix)
        self._add_stats()
        self._add_skills()
        self._add_spells()
        self._add_additional_features()
        self._calculate_attributes()
        if self.is_animist:
            self._add_spirits()
        if self.et.cult_amount:
            self._add_cults()
        return self

    def _add_stats(self):
        for stat in self.et.stats:
            self.stats[stat.name] = stat.roll()
            self.stats_list.append({'name': stat.name, 'value': self.stats[stat.name]})
        self.stats['CON'] = self.stats['POW']
        self.stats['STR'] = self.stats['POW']
        self.stats['SIZ'] = self.stats['POW']
        self.stats['DEX'] = self.stats['INT']
        
    def _calculate_attributes(self):
        sr = (self.stats['INT'] + self.stats['CHA']) // 2
        self._calculate_action_points()
        self._calculate_spirit_damage()
        self.attributes['magic_points'] = self.stats['POW']
        self.attributes['strike_rank'] = '%s' % sr
        self.attributes['movement'] = self.et.movement
        if 'Devotion' in self.skills_dict:
            self.is_theist = True
            self.attributes['devotional_pool'] = self._get_devotional_pool()
            self.attributes['max_intensity'] = int(math.ceil(self.skills_dict['Devotion'] / 10))
        if 'Shaping' in self.skills_dict:
            self.is_sorcerer = True
            self.attributes['max_shaping'] = int(math.ceil(self.skills_dict['Shaping'] / 10))
        if 'Mysticism' in self.skills_dict and 'Meditation' in self.skills_dict:
            self.is_mystic = True
            self.attributes['max_intensity'] = int(math.ceil(self.skills_dict['Mysticism'] / 20))
            self.attributes['max_total_intensity'] = int(math.ceil(self.skills_dict['Meditation'] / 10))
        if 'Binding' in self.skills_dict:
            self.is_animist = True
            self.attributes['max_pow'] = int(math.ceil(self.skills_dict['Binding'] / 10)) * 3
            self.attributes['max_spirits'] = self._get_max_spirits()
        self.attributes['spirit_intensity'] = (self.stats['POW'] - 1) // 6
        
    def _calculate_action_points(self):
        pow_int = self.stats['POW'] + self.stats['INT']
        if pow_int <= 12:
            self.attributes['action_points'] = 1
        elif pow_int <= 24:
            self.attributes['action_points'] = 2
        elif pow_int <= 36:
            self.attributes['action_points'] = 3
        elif pow_int <= 48:
            self.attributes['action_points'] = 4
        else:
            self.attributes['action_points'] = 5
        
    def _calculate_spirit_damage(self):
        damage_table = ['0', '1d2', '1d4', '1d6', '1d8', '1d10', '2d6', '1d8+1d6', '2d8', '1d10+1d8', '2d10',
                        '2d10+1d2', '2d10+1d4', '2d10+1d6', '2d10+1d8', '3d10', '3d10+1d2', '3d10+1d4']
        skill = self.skills_dict.get('Spectral combat', 0)
        index = _divide_round_up(skill, 20)
        try:
            spirit_damage = damage_table[index]
        except IndexError:
            spirit_damage = '3d10+1d6'
        self.attributes['spirit_damage'] = spirit_damage


class _Elemental(_Enemy):
    """ Elemental type of enemy """

    def generate(self, suffix=None):
        self._generate_name(suffix)
        self._add_stats()
        self.stats['SIZ'] = self.stats['STR']
        self.stats['CON'] = self.stats['STR']
        self.stats['CHA'] = self.stats['POW']
        self._add_skills()
        self._add_spells()
        self._add_additional_features()
        self._add_hit_locations()
        self._calculate_attributes()
        if self.et.cult_amount:
            self._add_cults()
        self._add_combat_styles()
        return self
        
    def _add_hit_locations(self):
        # Elementals have only one hit location
        # This is a bit of a hac, but I didn't want to add another field just for elemental
        # hit poits, so I'm calculating them based on POW.
        # If POW is 1d6+6, HP is 1d6+12. So both of them have 1d6 always, and the additional
        # part is double for hit points.
        power = next((stat.die_set for stat in self.et.stats if stat.name == 'POW'), '')
        try:
            modifier = 2 * int(power.split('+')[1])
        except (IndexError, TypeError):
            modifier = 0
        for hl in self.et.hit_locations:
            hp = max(Dice('1d6').roll() + modifier, 1)
            ap = hl.roll()
            enemy_hl = {'name': hl.name, 'range': hl.range, 'hp': hp, 'ap': ap, 'parent': hl}
            self.hit_locations.append(enemy_hl)


class Star(models.Model):
    """ Functionality for starring templates (marking as favourite) """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    template = models.ForeignKey(EnemyTemplate, on_delete=models.CASCADE)
    
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
    return (n + (d - 1)) // d
