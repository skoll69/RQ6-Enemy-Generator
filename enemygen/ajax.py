from django.utils import simplejson
from dajaxice.decorators import dajaxice_register
from enemygen.models import EnemyStat, EnemySkill, EnemyTemplate, Ruleset, StatAbstract
from enemygen.models import SpellAbstract, SkillAbstract, EnemySpell, EnemyHitLocation
from enemygen.models import CombatStyle, Weapon, Setting, CustomSpell, EnemyWeapon, CustomWeapon
from enemygen.models import Race, RaceStat, HitLocation, CustomSkill, Party, TemplateToParty

import logging
from enemygen.enemygen_lib import to_bool, int_or_zero

@dajaxice_register
def apply_notes_to_templates(request, race_id, notes):
    try:
        race = Race.objects.get(id=int(race_id))
        for et in EnemyTemplate.objects.filter(race=race, owner=request.user):
            if notes not in et.notes:
                et.notes = et.notes + '\n' + notes
                et.save()
        return simplejson.dumps({'success': True})
    except Exception as e:
        return simplejson.dumps({'error': str(e), 'notes': et.notes})
    
@dajaxice_register
def add_custom_spell(request, et_id, type):
    try:
        CustomSpell.create(et_id, type)
        return simplejson.dumps({'success': True})
    except Exception as e:
        return simplejson.dumps({'error': str(e)})
    
@dajaxice_register
def add_custom_skill(request, et_id):
    try:
        CustomSkill.create(et_id)
        return simplejson.dumps({'success': True})
    except Exception as e:
        return simplejson.dumps({'error': str(e)})
    
@dajaxice_register
def add_custom_weapon(request, cs_id, type):
    try:
        CustomWeapon.create(cs_id, type)
        return simplejson.dumps({'success': True})
    except Exception as e:
        return simplejson.dumps({'error': str(e)})
    
@dajaxice_register
def add_hit_location(request, race_id):
    try:
        HitLocation.create(race_id)
        return simplejson.dumps({'success': True})
    except Exception as e:
        return simplejson.dumps({'error': str(e)})
    
@dajaxice_register
def del_item(request, item_id, item_type):
    try:
        id = int(item_id)
        if item_type == 'hit_location':
            hl = HitLocation.objects.get(id=id)
            hl.delete()
            return simplejson.dumps({'success': True})
        elif item_type == 'custom_weapon':
            cw = CustomWeapon.objects.get(id=id)
            cw.delete()
            return simplejson.dumps({'success': True})
        elif item_type == 'party_template_spec':
            ttp = TemplateToParty.objects.get(id=id)
            ttp.delete()
            return simplejson.dumps({'success': True})
    except Exception as e:
        return simplejson.dumps({'error': str(e)})
    
    
@dajaxice_register
def submit(request, value, id, object, parent_id=None, extra={}):
    logger = logging.getLogger(__name__)
    try:
        id = int(id)
        success = True
        message = ''
        original_value = None
        #Attributes
        if object == 'et_published':
            et = EnemyTemplate.objects.get(id=id, owner=request.user)
            et.published = to_bool(value)
            et.save()
        elif object == 'et_stat_value':
            es = EnemyStat.objects.get(id=id)
            original_value = es.die_set
            try:
                es.set_value(value)
            except ValueError:
                success = False
                message = '%s is not a valid die value.' % value
        elif object == 'et_hl_armor':
            ehl = EnemyHitLocation.objects.get(id=id)
            try:
                ehl.set_armor(value)
            except ValueError:
                original_value = ehl.armor
                success = False
                message = "Not a valid dice set"
        elif object == 'et_movement':
            et = EnemyTemplate.objects.get(id=id, owner=request.user)
            et.movement = value
            et.save()
                
        #Skills
        elif object == 'et_skill_value':
            es = EnemySkill.objects.get(id=id)
            original_value = es.die_set
            try:
                es.set_value(value.upper())
            except ValueError:
                success = False
                message = '%s is not a valid die value.' % value
        elif object == 'et_skill_include':
            es = EnemySkill.objects.get(id=id)
            es.include = to_bool(value)
            es.save()

        #Custom Skills
        elif object == 'et_custom_skill_value':
            cs = CustomSkill.objects.get(id=id)
            try:
                cs.set_value(value.upper())
            except ValueError:
                original_value = cs.die_set
                success = False
                message = '%s is not a valid die value.' % value
        elif object == 'et_custom_skill_include':
            cs = CustomSkill.objects.get(id=id)
            cs.include = to_bool(value)
            cs.save()
        elif object == 'et_custom_skill_name':
            cs = CustomSkill.objects.get(id=id)
            cs.name = value
            cs.save()

        #Spells
        elif object == 'et_spell_prob':
            sa = SpellAbstract.objects.get(id=id)
            et = EnemyTemplate.objects.get(id=parent_id, owner=request.user)
            try:
                es = EnemySpell.objects.get(spell=sa, enemy_template=et)
            except EnemySpell.DoesNotExist:
                es = EnemySpell(spell=sa, enemy_template=et, detail=sa.default_detail, probability=1)
            original_value = es.probability
            try:
                es.set_probability(int(value))
            except ValueError:
                success = False
                message = 'Probability must be a number.'
        elif object == 'et_custom_spell_prob':
            cs = CustomSpell.objects.get(id=id)
            original_value = cs.probability
            try:
                cs.set_probability(int(value))
            except ValueError:
                success = False
                message = 'Probability must be a number.'
        elif object == 'et_custom_spell_name':
            cs = CustomSpell.objects.get(id=id)
            cs.name = value
            cs.save()
        elif object == 'et_name':
            et = EnemyTemplate.objects.get(id=id, owner=request.user)
            et.name = value
            et.save()
        elif object == 'et_rank':
            et = EnemyTemplate.objects.get(id=id, owner=request.user)
            et.rank = int(value)
            et.save()
        elif object == 'et_spell_detail':
            sa = SpellAbstract.objects.get(id=id)
            et = EnemyTemplate.objects.get(id=parent_id, owner=request.user)
            try:
                es = EnemySpell.objects.get(spell=sa, enemy_template=et)
            except:
                es = EnemySpell(spell=sa, enemy_template=et, detail=sa.default_detail, probability=1)
                es.set_probability(1)
            es.detail = value
            es.save()
        elif object == 'ruleset_name':
            ruleset = Ruleset.objects.get(id=id)
            ruleset.name = value
            ruleset.save()
        elif object == 'et_setting':
            et = EnemyTemplate.objects.get(id=id, owner=request.user)
            et.setting = Setting.objects.get(id=int(value))
            et.save()
        elif object == 'et_folk_spell_amount':
            et = EnemyTemplate.objects.get(id=id, owner=request.user)
            et.folk_spell_amount = value
            et.save()
        elif object == 'et_theism_spell_amount':
            et = EnemyTemplate.objects.get(id=id, owner=request.user)
            et.theism_spell_amount = value
            et.save()
        elif object == 'et_sorcery_spell_amount':
            et = EnemyTemplate.objects.get(id=id, owner=request.user)
            et.sorcery_spell_amount = value
            et.save()
            
        #Weapons and Combat Styles
        elif object == 'et_combat_style_name':
            cs = CombatStyle.objects.get(id=id)
            cs.name = value
            cs.save()
        elif object == 'et_combat_style_value':
            cs = CombatStyle.objects.get(id=id)
            cs.die_set = value.upper()
            cs.save()
        elif object == 'et_one_h_amount':
            cs = CombatStyle.objects.get(id=id, enemy_template__owner=request.user)
            cs.one_h_amount = value.lower()
            cs.save()
        elif object == 'et_two_h_amount':
            cs = CombatStyle.objects.get(id=id, enemy_template__owner=request.user)
            cs.two_h_amount = value.lower()
            cs.save()
        elif object == 'et_ranged_amount':
            cs = CombatStyle.objects.get(id=id, enemy_template__owner=request.user)
            cs.ranged_amount = value.lower()
            cs.save()
        elif object == 'et_shield_amount':
            cs = CombatStyle.objects.get(id=id, enemy_template__owner=request.user)
            cs.shield_amount = value.lower()
            cs.save()
        elif object == 'et_weapon_prob':
            we = Weapon.objects.get(id=id)
            cs = CombatStyle.objects.get(id=parent_id, enemy_template__owner=request.user)
            try:
                ew = EnemyWeapon.objects.get(weapon=we, combat_style=cs)
            except EnemyWeapon.DoesNotExist:
                ew = EnemyWeapon.create(cs, we, 1)
            original_value = ew.probability
            try:
                ew.set_probability(int(value))
            except ValueError:
                success = False
                message = 'Probability must be a number.'

        # Custom weapon
        elif object == 'et_custom_weapon_prob':
            cw = CustomWeapon.objects.get(id=id)
            original_value = cw.probability
            try:
                cw.set_probability(int(value))
            except ValueError:
                success = False
                message = 'Probability must be a number.'
        elif object == 'et_custom_weapon_name':
            cw = CustomWeapon.objects.get(id=id)
            cw.name = value
            cw.save()
        elif object == 'et_custom_weapon_damage':
            cw = CustomWeapon.objects.get(id=id)
            cw.damage = value.lower()
            cw.save()
        elif object == 'et_custom_weapon_ap':
            cw = CustomWeapon.objects.get(id=id)
            try:
                cw.ap = int(value)
            except ValueError:
                original_value = cw.ap
                success = False
                message = 'Probability must be a number.'
            cw.save()
        elif object == 'et_custom_weapon_hp':
            cw = CustomWeapon.objects.get(id=id)
            try:
                cw.hp = int(value)
            except ValueError:
                original_value = cw.hp
                success = False
                message = 'Probability must be a number.'
            cw.save()
        elif object == 'et_custom_weapon_size':
            cw = CustomWeapon.objects.get(id=id)
            cw.size = value
            cw.save()
        elif object == 'et_custom_weapon_reach':
            cw = CustomWeapon.objects.get(id=id)
            cw.reach = value
            cw.save()
        elif object == 'et_custom_weapon_type':
            cw = CustomWeapon.objects.get(id=id)
            cw.type = value
            cw.save()
        elif object == 'et_custom_weapon_damage_modifier':
            cw = CustomWeapon.objects.get(id=id)
            cw.damage_modifier = to_bool(value)
            cw.save()
            
        #Race
        elif object == 'race_name':
            race = Race.objects.get(id=id, owner=request.user)
            race.name = value
            race.save()
        elif object == 'race_published':
            race = Race.objects.get(id=id, owner=request.user)
            try:
                race.set_published(to_bool(value))
            except:
                success = False
                message = 'Something is wrong with the template'
                original_value = race.published
        elif object == 'race_movement':
            race = Race.objects.get(id=id, owner=request.user)
            race.movement = value
            race.save()
        elif object == 'race_stat_value':
            rs = RaceStat.objects.get(id=id, race__owner=request.user)
            try:
                rs.set_value(value)
            except ValueError:
                original_value = rs.default_value
                success = False
                message = "%s is not a valid die set." % value
        elif object == 'race_hl_range_start':
            hl = HitLocation.objects.get(id=id, race__owner=request.user)
            try:
                hl.range_start = int(value)
                hl.save()
            except ValueError:
                original_value = hl.range_start
                success = False
                message = "Range must be a number"
        elif object == 'race_hl_range_end':
            hl = HitLocation.objects.get(id=id, race__owner=request.user)
            try:
                hl.range_end = int(value)
                hl.save()
            except ValueError:
                original_value = hl.range_end
                success = False
                message = "Range must be a number"
        elif object == 'race_hl_name':
            hl = HitLocation.objects.get(id=id, race__owner=request.user)
            hl.name = value
            hl.save()
        elif object == 'race_hl_hp_modifier':
            hl = HitLocation.objects.get(id=id, race__owner=request.user)
            try:
                hl.hp_modifier = int_or_zero(value)
                hl.save()
            except ValueError:
                original_value = hl.hp_modifier
                success = False
                message = "HP Modifier must be a number"
        elif object == 'race_hl_armor':
            hl = HitLocation.objects.get(id=id, race__owner=request.user)
            try:
                hl.set_armor(value)
            except ValueError:
                original_value = hl.armor
                success = False
                message = "%s is not a valid die set." % value
        elif object == 'race_notes':
            race = Race.objects.get(id=id, owner=request.user)
            race.special = value
            race.save()
            
        # Party
        elif object == 'party_name':
            p = Party.objects.get(id=id, owner=request.user)
            p.name = value
            p.save()
        elif object == 'party_template_amount':
            p = Party.objects.get(id=int(parent_id), owner=request.user)
            t = EnemyTemplate.objects.get(id=id)
            p.set_amount(t, value)
            message = str(p) + ' ' + str(t)
        elif object == 'party_published':
            p = Party.objects.get(id=id, owner=request.user)
            try:
                p.set_published(to_bool(value))
            except:
                success = False
                message = 'Something is wrong with the template'
                original_value = p.published
        elif object == 'party_setting':
            p = Party.objects.get(id=id, owner=request.user)
            p.setting = Setting.objects.get(id=int(value))
            p.save()
        elif object == 'party_notes':
            party = Party.objects.get(id=id, owner=request.user)
            party.notes = value
            party.save()

        # Misc
        elif object == 'et_notes':
            et = EnemyTemplate.objects.get(id=id, owner=request.user)
            et.notes = value
            et.save()
            
        return simplejson.dumps({'success': success, 'message': message, 'original_value': original_value})
    except Exception as e:
        logger.error(str(e))
        return simplejson.dumps({'error': str(e)})
