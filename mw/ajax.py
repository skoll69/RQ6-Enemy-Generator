from dajaxice.decorators import dajaxice_register
from mw import models as m
from mw.views_lib import weapons
from enemygen.models import AdditionalFeatureList

import logging
import json
from bs4 import BeautifulSoup
from enemygen.enemygen_lib import to_bool


# noinspection PyUnusedLocal
@dajaxice_register
def add_custom_spell(request, et_id):
    try:
        m.CustomSpell.create(et_id)
        return json.dumps({'success': True})
    except Exception as e:
        return json.dumps({'error': str(e)})


# noinspection PyUnusedLocal
@dajaxice_register
def add_custom_skill(request, et_id):
    try:
        m.CustomSkill.create(et_id)
        return json.dumps({'success': True})
    except Exception as e:
        return json.dumps({'error': str(e)})


# noinspection PyUnusedLocal
@dajaxice_register
def add_template_to_party(request, party_id, template_ids):
    party = m.MWParty.objects.get(id=party_id)
    for template_id in template_ids:
        t = m.MWEnemyTemplate.objects.get(id=template_id)
        party.add(t)
    return json.dumps({'success': True})


# noinspection PyUnusedLocal,PyShadowingBuiltins
@dajaxice_register
def add_custom_weapon(request, cs_id, type):
    try:
        m.CustomWeapon.create(cs_id, type)
        return json.dumps({'success': True})
    except Exception as e:
        return json.dumps({'error': str(e)})


# noinspection PyUnusedLocal
@dajaxice_register
def del_item(request, item_id, item_type):
    try:
        item_id = int(item_id)
        if item_type == 'custom_weapon':
            cw = m.CustomWeapon.objects.get(id=item_id)
            cw.delete()
            return json.dumps({'success': True})
        elif item_type == 'party_template_spec':
            ttp = m.TemplateToParty.objects.get(id=item_id)
            ttp.delete()
            return json.dumps({'success': True})
        elif item_type == 'et_custom_spell':
            item = m.CustomSpell.objects.get(id=item_id)
            item.delete()
            return json.dumps({'success': True})
    except Exception as e:
        return json.dumps({'error': str(e)})


# noinspection PyBroadException,PyShadowingBuiltins
@dajaxice_register
def submit(request, value, id, object, parent_id=None):
    logger = logging.getLogger(__name__)
    try:
        id = int(id)
        success = True
        message = ''
        original_value = None
        
        # Basics
        if object == 'et_name':
            et = m.MWEnemyTemplate.objects.get(id=id, owner=request.user)
            et.name = value
            et.save()
        elif object == 'et_namelist':
            et = m.MWEnemyTemplate.objects.get(id=id, owner=request.user)
            try:
                namelist = AdditionalFeatureList.objects.get(type='name', id=value)
            except AdditionalFeatureList.DoesNotExist:
                namelist = None
            et.namelist = namelist
            et.save()
        elif object == 'et_rank':
            et = m.MWEnemyTemplate.objects.get(id=id, owner=request.user)
            et.rank = int(value)
            et.save()
        elif object == 'et_published':
            et = m.MWEnemyTemplate.objects.get(id=id, owner=request.user)
            et.published = to_bool(value)
            et.save()

        # Attributes
        elif object == 'et_stat_value':
            es = m.EnemyStat.objects.get(id=id)
            original_value = es.die_set
            try:
                es.set_value(value)
            except ValueError:
                success = False
                message = '%s is not a valid die value.' % value
        elif object == 'et_movement':
            et = m.MWEnemyTemplate.objects.get(id=id, owner=request.user)
            et.movement = value
            et.save()
        elif object == 'et_armor':
            et = m.MWEnemyTemplate.objects.get(id=id, owner=request.user)
            et.armor = value
            et.save()

        # Skills
        elif object == 'et_skill_value':
            es = m.EnemySkill.objects.get(id=id)
            original_value = es.die_set
            try:
                es.set_value(value.upper())
            except ValueError:
                success = False
                message = '%s is not a valid die value.' % value
        elif object == 'et_skill_include':
            es = m.EnemySkill.objects.get(id=id)
            es.include = to_bool(value)
            es.save()

        # Custom Skills
        elif object == 'et_custom_skill_value':
            cs = m.CustomSkill.objects.get(id=id)
            try:
                cs.set_value(value.upper())
            except ValueError:
                original_value = cs.die_set
                success = False
                message = '%s is not a valid die value.' % value
        elif object == 'et_custom_skill_include':
            cs = m.CustomSkill.objects.get(id=id)
            cs.include = to_bool(value)
            cs.save()
        elif object == 'et_custom_skill_name':
            cs = m.CustomSkill.objects.get(id=id)
            cs.name = value
            cs.save()

        # Spells
        elif object == 'et_spell_prob':
            sa = m.SpellAbstract.objects.get(id=id)
            et = m.MWEnemyTemplate.objects.get(id=parent_id, owner=request.user)
            try:
                es = m.EnemySpell.objects.get(spell=sa, enemy_template=et)
            except m.EnemySpell.DoesNotExist:
                es = m.EnemySpell(spell=sa, enemy_template=et, detail=sa.default_detail, probability=1)
            original_value = es.probability
            try:
                es.set_probability(int(value))
            except ValueError:
                success = False
                message = 'Probability must be a number.'
        elif object == 'et_custom_spell_prob':
            cs = m.CustomSpell.objects.get(id=id)
            original_value = cs.probability
            try:
                cs.set_probability(int(value))
            except ValueError:
                success = False
                message = 'Probability must be a number.'
        elif object == 'et_custom_spell_name':
            cs = m.CustomSpell.objects.get(id=id)
            cs.name = value
            cs.save()
        elif object == 'et_spell_detail':
            sa = m.SpellAbstract.objects.get(id=id)
            et = m.MWEnemyTemplate.objects.get(id=parent_id, owner=request.user)
            try:
                es = m.EnemySpell.objects.get(spell=sa, enemy_template=et)
            except:
                es = m.EnemySpell(spell=sa, enemy_template=et, detail=sa.default_detail, probability=1)
                es.set_probability(1)
            es.detail = value
            es.save()
        elif object == 'et_spell_amount':
            et = m.MWEnemyTemplate.objects.get(id=id, owner=request.user)
            et.spell_amount = value
            et.save()

        # Weapons and Combat Styles
        elif object == 'et_combat_style_name':
            cs = m.CombatStyle.objects.get(id=id)
            cs.name = value
            cs.save()
        elif object == 'et_combat_style_value':
            cs = m.CombatStyle.objects.get(id=id)
            try:
                cs.set_value(value)
            except:
                success = False
                message = 'Probability must be a number.'
                original_value = cs.die_set
        elif object == 'et_one_h_amount':
            cs = m.CombatStyle.objects.get(id=id, enemy_template__owner=request.user)
            cs.one_h_amount = value.lower()
            cs.save()
        elif object == 'et_two_h_amount':
            cs = m.CombatStyle.objects.get(id=id, enemy_template__owner=request.user)
            cs.two_h_amount = value.lower()
            cs.save()
        elif object == 'et_ranged_amount':
            cs = m.CombatStyle.objects.get(id=id, enemy_template__owner=request.user)
            cs.ranged_amount = value.lower()
            cs.save()
        elif object == 'et_shield_amount':
            cs = m.CombatStyle.objects.get(id=id, enemy_template__owner=request.user)
            cs.shield_amount = value.lower()
            cs.save()
        elif object == 'et_weapon_prob':
            we = m.Weapon.objects.get(id=id)
            cs = m.CombatStyle.objects.get(id=parent_id, enemy_template__owner=request.user)
            try:
                ew = m.EnemyWeapon.objects.get(weapon=we, combat_style=cs)
            except m.EnemyWeapon.DoesNotExist:
                ew = m.EnemyWeapon.create(cs, we, 1)
            original_value = ew.probability
            try:
                ew.set_probability(int(value))
            except ValueError:
                success = False
                message = 'Probability must be a number.'
        elif object == 'et_weapon_die_set':
            we = m.Weapon.objects.get(id=id)
            cs = m.CombatStyle.objects.get(id=parent_id, enemy_template__owner=request.user)
            try:
                ew = m.EnemyWeapon.objects.get(weapon=we, combat_style=cs)
            except m.EnemyWeapon.DoesNotExist:
                ew = m.EnemyWeapon.create(cs, we, 1)
            original_value = ew.die_set
            try:
                ew.set_die_set(value)
            except ValueError:
                success = False
                message = 'Not a valid die-set.'

        # Custom weapon
        elif object == 'et_custom_weapon_prob':
            cw = m.CustomWeapon.objects.get(id=id)
            original_value = cw.probability
            try:
                cw.set_probability(int(value))
            except ValueError:
                success = False
                message = 'Probability must be a number.'
        elif object == 'et_custom_weapon_name':
            cw = m.CustomWeapon.objects.get(id=id)
            cw.name = value
            cw.save()
        elif object == 'et_custom_weapon_die_set':
            cw = m.CustomWeapon.objects.get(id=id)
            cw.set_die_set(value)
        elif object == 'et_custom_weapon_name':
            cw = m.CustomWeapon.objects.get(id=id)
            cw.name = value
            cw.save()
        elif object == 'et_custom_weapon_damage':
            cw = m.CustomWeapon.objects.get(id=id)
            cw.damage = value
            cw.save()
        elif object == 'et_custom_weapon_hp':
            cw = m.CustomWeapon.objects.get(id=id)
            try:
                cw.hp = int(value)
            except ValueError:
                original_value = cw.hp
                success = False
                message = 'Probability must be a number.'
            cw.save()
        elif object == 'et_custom_weapon_length':
            cw = m.CustomWeapon.objects.get(id=id)
            cw.length = value
            cw.save()
        elif object == 'et_custom_weapon_range':
            cw = m.CustomWeapon.objects.get(id=id)
            cw.range = value
            cw.save()
        elif object == 'et_custom_weapon_type':
            cw = m.CustomWeapon.objects.get(id=id)
            cw.type = value
            cw.save()
        elif object == 'et_custom_weapon_damage_bonus':
            cw = m.CustomWeapon.objects.get(id=id)
            cw.damage_bonus = value
            cw.save()

        # Party
        elif object == 'party_name':
            p = m.MWParty.objects.get(id=id, owner=request.user)
            p.name = value
            p.save()
        elif object == 'party_template_amount':
            p = m.MWParty.objects.get(id=parent_id, owner=request.user)
            t = m.MWEnemyTemplate.objects.get(id=id)
            p.set_amount(t, value)
            message = str(p) + ' ' + str(t)
        elif object == 'party_published':
            p = m.MWParty.objects.get(id=id, owner=request.user)
            try:
                p.set_published(to_bool(value))
            except:
                success = False
                message = 'Something is wrong with the template'
                original_value = p.published
        elif object == 'party_notes':
            party = m.MWParty.objects.get(id=id, owner=request.user)
            party.notes = value
            party.save()
        elif object == 'party_newtag':
            p = m.MWParty.objects.get(id=id, owner=request.user)
            for tag in value.split(','):
                p.tags.add(tag.strip().capitalize())
        elif object == 'party_deltag':
            p = m.MWParty.objects.get(id=id, owner=request.user)
            p.tags.remove(value.capitalize())

        # Misc
        elif object == 'et_notes':
            et = m.MWEnemyTemplate.objects.get(id=id, owner=request.user)
            et.notes = value
            et.save()
        elif object == 'et_newtag':
            et = m.MWEnemyTemplate.objects.get(id=id, owner=request.user)
            for tag in value.split(','):
                et.tags.add(tag.strip().capitalize())
        elif object == 'et_deltag':
            et = m.MWEnemyTemplate.objects.get(id=id, owner=request.user)
            et.tags.remove(value.capitalize())

        return json.dumps({'success': success, 'message': message, 'original_value': original_value})
    except Exception as e:
        logger.error(str(e))
        return json.dumps({'error': str(e)})


# noinspection PyUnusedLocal,PyShadowingBuiltins
@dajaxice_register
def change_template(request, html_file, id, value):
    """ Changes the name of the generated enemy, in the given html
        Input: html_file    - name of the html file to modify
               id           - id of the html element to modify
               value        - new value
    """
    with open(html_file.encode('utf-8'), 'r') as ff:
        soup = BeautifulSoup(ff)
    span_tag = soup.find('span', {'id': id})
    klasses = ' '.join(span_tag['class'])
    new_tag = BeautifulSoup('<span id="%s" class="%s">%s</span>' % (id, klasses, value)).span
    soup.find('span', {'id': id}).replaceWith(new_tag)
    with open(html_file.encode('utf-8'), 'w') as ff:
        ff.write(soup.prettify('utf-8', formatter='html'))
    return json.dumps({'html_file': html_file})


@dajaxice_register
def toggle_star(request, et_id):
    if request.user.is_authenticated():
        m.MWEnemyTemplate.objects.get(id=et_id).toggle_star(request.user)
        return json.dumps({'success': True})
    else:
        return json.dumps({'success': False})


@dajaxice_register(method='GET')
def search(request, string, rank_filter):
    templs = m.MWEnemyTemplate.search(string, request.user, rank_filter)
    templates = [et.summary_dict(request.user) for et in templs]
    return json.dumps({'results': templates, 'success': True})


# noinspection PyUnusedLocal,PyShadowingBuiltins
@dajaxice_register(method='GET')
def get_weapons(request, cs_id, filter):
    cs = m.CombatStyle.objects.get(id=cs_id)
    cs.enemy_template.weapon_filter = filter
    cs.enemy_template.save()
    context = {'weapons': weapons(cs), 'success': True}
    return json.dumps(context)
