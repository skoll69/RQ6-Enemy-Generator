"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from django.test import TestCase
from django.contrib.auth.models import User

import ordereddict

from dice import Dice, _die_to_tuple

from models import EnemyTemplate, _Enemy, Ruleset, StatAbstract, Race, SpellAbstract
from models import EnemyStat, EnemySkill, Setting, SkillAbstract, EnemySpell
from models import CombatStyle, Weapon

from enemygen_lib import _select_random_item, ValidationError, to_bool, replace_die_set

class TestDice(TestCase):
    def test_1_die_to_tuple(self):
        self.assertEquals(_die_to_tuple('d6'), (1,6,1))
        self.assertEquals(_die_to_tuple('D6'), (1,6,1))
        self.assertEquals(_die_to_tuple('+D6'), (1,6,1))
        self.assertEquals(_die_to_tuple('-D6'), (-6,-1,1))
        
        self.assertEquals(_die_to_tuple('2D6'), (1,6,2))
        self.assertEquals(_die_to_tuple('12D6'), (1,6,12))
        self.assertEquals(_die_to_tuple('+3D8'), (1,8,3))
        self.assertEquals(_die_to_tuple('-2D6'), (-6,-1,2))
        
    def test_2_dissect(self):
        self.assertEquals(Dice('D6')._dissect(), [(1,6,1),])
        self.assertEquals(Dice('d6')._dissect(), [(1,6,1),])
        self.assertEquals(Dice('d6+1')._dissect(), [(1,6,1), 1])
        self.assertEquals(Dice('d6-1')._dissect(), [(1,6,1), -1])
        self.assertEquals(Dice('50+d6-1')._dissect(), [50, (1,6,1), -1])
        self.assertEquals(Dice('50-d6')._dissect(), [50, (-6,-1,1)])
        self.assertEquals(Dice('2D6-D4')._dissect(), [(1,6,2), (-4,-1,1)])
        self.assertEquals(Dice('2D6-D4+5')._dissect(), [(1,6,2), (-4,-1,1), 5])
        self.assertEquals(Dice('2D6-D4-5')._dissect(), [(1,6,2), (-4,-1,1), -5])
        
    def test_3_dice(self):
        self.assertTrue(1 <= Dice('D6').roll() <= 6)
        self.assertTrue(1 <= Dice('D6').roll() <= 6)
        self.assertTrue(1 <= Dice('D6').roll() <= 6)
        
        self.assertTrue(7 <= Dice('6+D6').roll() <= 12)
        self.assertTrue(7 <= Dice('6+D6').roll() <= 12)
        self.assertTrue(7 <= Dice('6+D6').roll() <= 12)

        self.assertTrue(12 <= Dice('20-2D4').roll() <= 18)
        self.assertTrue(12 <= Dice('20-2D4').roll() <= 18)
        self.assertTrue(12 <= Dice('20-2D4').roll() <= 18)
        
        self.assertTrue(2 <= Dice('2D20').roll() <= 40)
        self.assertTrue(2 <= Dice('2D20').roll() <= 40)
        self.assertTrue(2 <= Dice('2D20').roll() <= 40)
        self.assertTrue(2 <= Dice('2D20').roll() <= 40)
        self.assertTrue(2 <= Dice('2D20').roll() <= 40)
        
        self.assertTrue(12 <= Dice('10 + 2D2').roll() <= 14)
        self.assertTrue(12 <= Dice('10 + 2D2').roll() <= 14)
        self.assertTrue(12 <= Dice('10 + 2D2').roll() <= 14)
        self.assertTrue(12 <= Dice('10 + 2D2').roll() <= 14)
        
        self.assertTrue(12 <= Dice('12D6').roll() <= 72)
        self.assertTrue(12 <= Dice('12D6').roll() <= 72)
        self.assertTrue(12 <= Dice('12D6').roll() <= 72)
        self.assertTrue(12 <= Dice('12D6').roll() <= 72)
        
    def test_4_max_roll(self):
        self.assertEquals(Dice('5').max_roll(), 5)
        self.assertEquals(Dice('D100').max_roll(), 100)
        self.assertEquals(Dice('5D100').max_roll(), 500)
        self.assertEquals(Dice('5D100+13').max_roll(), 513)
        self.assertEquals(Dice('5D100-D100').max_roll(), 499)
        self.assertEquals(Dice('12D6').max_roll(), 72)
        
class TestEnemyTemplate(TestCase):
    fixtures = ('enemygen_testdata.json',)
    def test_01_create(self):
        user = User(username='username'); user.save()
        ruleset = Ruleset.objects.get(id=1)
        self.assertEquals(ruleset.name, 'RuneQuest 6')
        race = Race.objects.get(id=1)
        self.assertEquals(race.name, 'Human')
        setting = Setting.objects.get(id=1)
        et = EnemyTemplate.create(user, ruleset, setting, race, 'Template Name')
        self.assertEquals(et.name, 'Template Name')
        self.assertTrue(isinstance(et.stats[0], EnemyStat))
        self.assertEquals(et.stats[0].name, 'STR')
        self.assertEquals(et.stats[0].die_set, '3d6')
        self.assertTrue(isinstance(et.skills[0], EnemySkill))
        self.assertEquals(et.skills[0].name, 'Athletics')
        self.assertEquals(et.skills[0].die_set, 'STR+DEX')
        self.assertTrue(et.combat_styles[0].name, "Primary Combat Style")

    def test_12_generate(self):
        et = get_enemy_template()
        enemy = et.generate()
        self.assertTrue(isinstance(enemy, _Enemy))
        self.assertTrue(isinstance(enemy.stats, ordereddict.OrderedDict))
        self.assertTrue(isinstance(enemy.skills, list))
        self.assertTrue(isinstance(enemy.skills[0], dict))
        self.assertTrue(isinstance(enemy.stats['STR'], int))
        self.assertEquals(enemy.skills[0]['name'], 'Athletics')
        self.assertTrue(isinstance(enemy.skills[0]['value'], int))
        
    def test_13_generate_2(self):
        et = get_enemy_template()
        self.assertEquals(et.skills[9].name, 'Evade')
        skill = et.skills[9]
        skill.die_set = 'STR+DEX+50'
        skill.save()
        self.assertEquals(et.stats[0].name, 'STR')
        stat = et.stats[0]
        stat.die_set = '2+2D4'
        stat.save()
        self.assertEquals(et.stats[3].name, 'DEX')
        stat = et.stats[3]
        stat.die_set = '10+D3'
        stat.save()

        enemy = et.generate()
        self.assertTrue(4 <= enemy.stats['STR'] <= 10)
        self.assertTrue(11 <= enemy.stats['DEX'] <= 13)
        self.assertEquals(enemy.skills[3]['name'], 'Evade')
        self.assertEquals(enemy.skills[3]['value'], enemy.stats['DEX'] + enemy.stats['STR'] + 50)
        
    def test_14_generate_check_spells(self):
        et = get_enemy_template()
        et.folk_spell_amount = '2'
        self.assertEquals(len(et.folk_spells), 0)
        es = EnemySpell(enemy_template=et, spell=SpellAbstract.objects.get(name='Alarm'), probability=1); es.save()
        es = EnemySpell(enemy_template=et, spell=SpellAbstract.objects.get(name='Avert'), probability=1); es.save()

        enemy = et.generate()
        self.assertEquals(len(enemy.folk_spells), 2)
        
        self.assertTrue(enemy.folk_spells[0].name in ('Alarm', 'Avert'))
        self.assertTrue(enemy.folk_spells[1].name in ('Alarm', 'Avert'))
        
    def test_15_generate_check_attributes(self):
        et = get_enemy_template()
        self.assertEquals(et.ruleset.name, 'RuneQuest 6')
        enemy = et.generate()
        
        action_points = enemy.attributes['action_points']
        self.assertTrue((action_points == 1 and enemy.stats['INT'] + enemy.stats['DEX'] <= 12) or
                        (action_points == 2 and enemy.stats['INT'] + enemy.stats['DEX'] <= 24) or
                        (action_points == 3 and enemy.stats['INT'] + enemy.stats['DEX'] <= 36) or
                        (action_points == 4 and enemy.stats['INT'] + enemy.stats['DEX'] > 36)
                       )
                       
        damage_modifier = enemy.attributes['damage_modifier']
        str_siz = enemy.stats['STR'] + enemy.stats['SIZ']
        self.assertTrue((damage_modifier == '-1d8' and str_siz <= 5) or
                        (damage_modifier == '-1d4' and 11 <= str_siz <= 15) or
                        (damage_modifier == '-1d2' and 16 <= str_siz <= 20) or
                        (damage_modifier == '+0' and 21 <= str_siz <= 25) or
                        (damage_modifier == '+1d2' and 26 <= str_siz <= 30) or
                        (damage_modifier == '+1d4' and 31 <= str_siz <= 35) or
                        (damage_modifier == '+1d6' and 36 <= str_siz <= 40)
                       )
                       
        self.assertEquals(enemy.attributes['magic_points'], enemy.stats['POW'])
        
        sr = (enemy.stats['INT'] + enemy.stats['DEX']) / 2
        sr = '%s(%s-0)' % (sr, sr)
        self.assertEquals(enemy.attributes['strike_rank'], sr)
        
    def notest_16_generate_check_weapon_styles(self):
        # Fix this test!!!!!!!!!!!!!!!
        et = get_enemy_template()
        cs1 = CombatStyle(name="name", enemy_template=et, die_set="STR+DEX"); cs1.save()
        cs1.weapon_options.add(Weapon.objects.get(name="Broadsword"))
        enemy = et.generate()
        
        self.assertEquals(enemy.combat_styles[0]['name'], "Primary Combat Style")
        self.assertEquals(enemy.combat_styles[0]['value'], enemy.stats['STR']+enemy.stats['DEX'])
        self.assertEquals(enemy.combat_styles[0]['weapons'][0].name, 'Broadsword')
        
class Test_Enemy(TestCase):
    fixtures = ('enemygen_testdata.json',)
    
    def no_test_1_die_set_with_stat_values(self):
        et = get_enemy_template()
        enemy = _Enemy(et)
        enemy.stats.append({'name': 'STR', 'value': 10})
        enemy.stats.append({'name': 'DEX', 'value': 20})
        self.assertEquals(enemy._die_set_with_stat_values('STR+DEX'), '10+20')
        self.assertEquals(enemy._die_set_with_stat_values('STR+DEX+50'), '10+20+50')
        
    def test_enemy_get_stats(self):
        et = get_enemy_template()
        enemy = _Enemy(et).generate()
        self.assertEquals(enemy.get_stats[0]['name'], 'STR')
        self.assertEquals(enemy.get_stats[1]['name'], 'CON')
        self.assertTrue(isinstance(enemy.get_stats[0]['value'], int))
        
    def test_calculate_damage_modifier(self):
        class EM:
            name = 'name'
            get_cult_rank = 1
            notes = ''
        enemy_mock = EM()
        enemy = _Enemy(enemy_mock)
        enemy.stats = {}
        enemy.attributes = {}
        
        enemy.stats['STR'] = 2
        enemy.stats['SIZ'] = 2
        enemy._calculate_damage_modifier()
        self.assertEquals(enemy.attributes['damage_modifier'], '-1d8')
        
        enemy.stats['STR'] = 3
        enemy.stats['SIZ'] = 2
        enemy._calculate_damage_modifier()
        self.assertEquals(enemy.attributes['damage_modifier'], '-1d8')
    
        enemy.stats['STR'] = 12
        enemy.stats['SIZ'] = 14
        enemy._calculate_damage_modifier()
        self.assertEquals(enemy.attributes['damage_modifier'], '+1d2')
    
        enemy.stats['STR'] = 20
        enemy.stats['SIZ'] = 11
        enemy._calculate_damage_modifier()
        self.assertEquals(enemy.attributes['damage_modifier'], '+1d4')
    
        enemy.stats['STR'] = 20
        enemy.stats['SIZ'] = 15
        enemy._calculate_damage_modifier()
        self.assertEquals(enemy.attributes['damage_modifier'], '+1d4')
    
        enemy.stats['STR'] = 40
        enemy.stats['SIZ'] = 11
        enemy._calculate_damage_modifier()
        self.assertEquals(enemy.attributes['damage_modifier'], '+1d12')
    
        enemy.stats['STR'] = 40
        enemy.stats['SIZ'] = 20
        enemy._calculate_damage_modifier()
        self.assertEquals(enemy.attributes['damage_modifier'], '+1d12')
    
        enemy.stats['STR'] = 40
        enemy.stats['SIZ'] = 21
        enemy._calculate_damage_modifier()
        self.assertEquals(enemy.attributes['damage_modifier'], '+2d6')
    
        enemy.stats['STR'] = 65
        enemy.stats['SIZ'] = 65
        enemy._calculate_damage_modifier()
        self.assertEquals(enemy.attributes['damage_modifier'], '+2d10+1d4')
        
    def test_hit_locations(self):
        et = get_enemy_template()
        enemy = _Enemy(et).generate()
        
        self.assertTrue(isinstance(enemy.hit_locations, list))
        self.assertEquals(enemy.hit_locations[0]['name'], 'Right leg')
        self.assertEquals(enemy.hit_locations[0]['range'], '01&#8209;03')
        
        HITPOINTS = {1: (1,3,2,1,1), 6: (2,4,3,1,2), 11: (3,5,4,2,3),
                     31: (7,9,8,6,7), 41: (9,11,10,8,9)}
        
    def test_hit_locations_hp(self):
        et = get_enemy_template()
        enemy = _Enemy(et).generate()
        
        enemy.hit_locations = []
        enemy.stats['CON'] = 2
        enemy.stats['SIZ'] = 2
        enemy._add_hit_locations()
        self.assertEquals(enemy.hit_locations[0]['hp'], 1) #Leg
        self.assertEquals(enemy.hit_locations[3]['hp'], 3) #Chest
        
        enemy.hit_locations = []
        enemy.stats['CON'] = 11
        enemy.stats['SIZ'] = 11
        enemy._add_hit_locations()
        self.assertEquals(enemy.hit_locations[0]['hp'], 5) #Leg
        self.assertEquals(enemy.hit_locations[2]['hp'], 6) #Abdomen
        self.assertEquals(enemy.hit_locations[3]['hp'], 7) #Chest
        self.assertEquals(enemy.hit_locations[5]['hp'], 4) #Arm
        self.assertEquals(enemy.hit_locations[6]['hp'], 5) #Head
        
        enemy.hit_locations = []
        enemy.stats['CON'] = 22
        enemy.stats['SIZ'] = 22
        enemy._add_hit_locations()
        self.assertEquals(enemy.hit_locations[0]['hp'], 9) #Leg
        self.assertEquals(enemy.hit_locations[2]['hp'], 10) #Abdomen
        self.assertEquals(enemy.hit_locations[3]['hp'], 11) #Chest
        self.assertEquals(enemy.hit_locations[5]['hp'], 8) #Arm
        self.assertEquals(enemy.hit_locations[6]['hp'], 9) #Head
        
class TestEnemySkill(TestCase):
    fixtures = ('enemygen_testdata.json',)
    
    def test_1_roll(self):
        skill = SkillAbstract.objects.get(id=1)
        et = get_enemy_template()
        es = EnemySkill.objects.get(skill=skill, enemy_template=et)
        es.die_set = 'STR+DEX+2D4'
        es.save()
        replace_with = {'STR': 10, 'DEX': 20}
        self.assertEquals(replace_die_set(es.die_set, replace_with), '10+20+2D4')
        
    def test_2_roll(self):
        skill = SkillAbstract.objects.get(id=1)
        et = get_enemy_template()
        es = EnemySkill.objects.get(skill=skill, enemy_template=et)
        es.die_set = '10+2D4'
        es.save()
        
        self.assertTrue(12 <= es.roll() <= 18)
        self.assertTrue(12 <= es.roll() <= 18)
        self.assertTrue(12 <= es.roll() <= 18)
        self.assertTrue(12 <= es.roll() <= 18)
        self.assertTrue(12 <= es.roll() <= 18)
        self.assertTrue(12 <= es.roll() <= 18)
        
        es = EnemySkill.objects.get(skill=skill, enemy_template=et)
        es.die_set = 'STR+DEX+10+2D4'
        es.save()
        replace_with = {'STR': 10, 'DEX': 20}
        self.assertTrue(42 <= es.roll(replace_with) <= 48)
        self.assertTrue(42 <= es.roll(replace_with) <= 48)
        self.assertTrue(42 <= es.roll(replace_with) <= 48)
        self.assertTrue(42 <= es.roll(replace_with) <= 48)
        self.assertTrue(42 <= es.roll(replace_with) <= 48)
        self.assertTrue(42 <= es.roll(replace_with) <= 48)
        
    def test_set_value(self):
        stat = StatAbstract.objects.get(id=2)
        et = get_enemy_template()
        es = EnemyStat(stat=stat, enemy_template=et, die_set='D6')
        es.save()
        
        self.assertRaises(ValueError, es.set_value, 'invalid')
        
class TestMisc(TestCase):
    fixtures = ('enemygen_testdata.json',)
    
    def test_jalla(self):
        pass
        #from django.core import mail
        #print 'sending email'
        #mail.send_mail('Moro', 'How you doing?', 'skoll.fenrissen@gmail.com', ['erkki.lepre@gmail.com'], fail_silently=False)
        
        #from django.core.mail import EmailMessage
        #msg = EmailMessage('Request Callback', 'my message', to=['erkki.lepre@iki.fi'])
        #msg.send()
        
    def test_select_random_spell(self):
        et = get_enemy_template()
        self.assertEquals(len(et.folk_spells), 0)
        es = EnemySpell(enemy_template=et, spell=SpellAbstract.objects.get(name='Alarm'), probability=1); es.save()
        es = EnemySpell(enemy_template=et, spell=SpellAbstract.objects.get(name='Avert'), probability=1); es.save()
        
        spells = et.folk_spells
        
        self.assertTrue(_select_random_item(spells).name in (spells[0].name, spells[1].name))
        self.assertTrue(_select_random_item(spells).name in (spells[0].name, spells[1].name))
        self.assertTrue(_select_random_item(spells).name in (spells[0].name, spells[1].name))
        self.assertTrue(_select_random_item(spells).name in (spells[0].name, spells[1].name))
        
        es = EnemySpell(enemy_template=et, spell=SpellAbstract.objects.get(name='Calm'), probability=1); es.save()
        spells = et.folk_spells
        # Test exclude
        spells[0].probability = 100
        spells[0].save()
        spells[1].probability = 100
        spells[1].save()
        spells[2].probability = 1
        spells[2].save()

        exclude = (spells[0], spells[1])
        random_spell = _select_random_item(spells, exclude)
        self.assertEquals(random_spell, spells[2])
        
def get_enemy_template():
    user = User(username='username'); user.save()
    ruleset = Ruleset.objects.get(id=1)
    if ruleset.name != 'RuneQuest 6': raise Exception("Ruleset doesn't match")
    race = Race.objects.get(id=1)
    if race.name != 'Human': raise Exception("Race doesn't match")
    setting = Setting.objects.get(id=1)
    et = EnemyTemplate.create(user, ruleset, setting, race, 'Test Template')
    return et