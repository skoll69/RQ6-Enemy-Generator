# pylint: disable=no-member

from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required

from enemygen.models import EnemyStat, EnemySkill, EnemyTemplate
from enemygen.models import SpellAbstract, EnemySpell, EnemyHitLocation
from enemygen.models import CombatStyle, Weapon, CustomSpell, EnemyWeapon, CustomWeapon
from enemygen.models import Race, RaceStat, HitLocation, CustomSkill, Party, TemplateToParty, EnemySpirit
from enemygen.models import EnemyAdditionalFeatureList, PartyAdditionalFeatureList, AdditionalFeatureList
from enemygen.models import EnemyNonrandomFeature, PartyNonrandomFeature, EnemyCult
from enemygen.views_lib import weapons
from enemygen.dice import Dice
from enemygen.enemygen_lib import to_bool

import logging
import json
import html
import os
from bs4 import BeautifulSoup


@login_required
def apply_notes_to_templates(request, race_id):
    body = json.loads(request.body)
    notes = body['notes']
    try:
        race = Race.objects.get(id=int(race_id))
        for et in EnemyTemplate.objects.filter(race=race, owner=request.user):
            if notes not in et.notes:
                et.notes = et.notes + '\n' + notes
                et.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
def add_additional_feature(request, parent_id):
    body = json.loads(request.body)
    feature_list_id = body['feature_list_id']
    try:
        if body['type'] == 'et':
            et = EnemyTemplate.objects.get(id=parent_id, owner=request.user)
            et.add_additional_feature(feature_list_id)
        elif body['type'] == 'party':
            party = Party.objects.get(id=parent_id, owner=request.user)
            party.add_additional_feature(feature_list_id)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
def add_custom_spell(request, et_id, type):
    try:
        CustomSpell.create(et_id, type)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
def add_custom_skill(request, et_id):
    try:
        CustomSkill.create(et_id)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
def add_spirit(request, et_id):
    spirit_ids = json.loads(request.body)['spirit_ids']
    error = ''
    for spirit_id in spirit_ids:
        try:
            EnemySpirit.create(spirit_id, et_id)
        except Exception as e:
            error += str(e)
    if error:
        return JsonResponse({'error': error})
    else:
        return JsonResponse({'success': True})


@login_required
def add_cult(request, et_id):
    cult_ids = json.loads(request.body)['cult_ids']
    if not cult_ids:
        return JsonResponse({'success': False})
    error = ''
    for cult_id in cult_ids:
        try:
            EnemyCult.create(cult_id, et_id)
        except Exception as e:
            error += str(e)
    if error:
        return JsonResponse({'error': error})
    else:
        return JsonResponse({'success': True})


@login_required
def add_template_to_party(request, party_id):
    template_ids = json.loads(request.body)['template_ids']
    if not template_ids:
        return JsonResponse({'success': False})
    party = Party.objects.get(id=party_id)
    for template_id in template_ids:
        t = EnemyTemplate.objects.get(id=template_id)
        party.add(t)
    return JsonResponse({'success': True})


@login_required
def add_nonrandom_feature(request, feature_id):
    body = json.loads(request.body)
    et_id = body.get('et_id', None)
    party_id = body.get('party_id', None)
    if et_id:
        et = EnemyTemplate.objects.get(id=et_id)
        et.add_nonrandom_feature(feature_id)
        return JsonResponse({'success': True})
    elif party_id:
        party = Party.objects.get(id=party_id)
        party.add_nonrandom_feature(feature_id)
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


@login_required
def add_custom_weapon(request, cs_id, type):
    try:
        CustomWeapon.create(cs_id, type)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
def add_hit_location(request, race_id):
    try:
        HitLocation.create(race_id)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
def del_item(request, item_id, item_type):
    try:
        item_id = int(item_id)
        if item_type == 'hit_location':
            hl = HitLocation.objects.get(id=item_id)
            hl.delete()
            return JsonResponse({'success': True})
        elif item_type == 'custom_weapon':
            cw = CustomWeapon.objects.get(id=item_id)
            cw.delete()
            return JsonResponse({'success': True})
        elif item_type == 'party_template_spec':
            ttp = TemplateToParty.objects.get(id=item_id)
            ttp.delete()
            return JsonResponse({'success': True})
        elif item_type == 'et_spirit':
            es = EnemySpirit.objects.get(id=item_id)
            es.delete()
            return JsonResponse({'success': True})
        elif item_type == 'et_cult':
            es = EnemyCult.objects.get(id=item_id)
            es.delete()
            return JsonResponse({'success': True})
        elif item_type == 'et_additional_feature':
            item = EnemyAdditionalFeatureList.objects.get(id=item_id)
            item.delete()
            return JsonResponse({'success': True})
        elif item_type == 'party_additional_feature':
            item = PartyAdditionalFeatureList.objects.get(id=item_id)
            item.delete()
            return JsonResponse({'success': True})
        elif item_type == 'et_custom_spell':
            item = CustomSpell.objects.get(id=item_id)
            item.delete()
            return JsonResponse({'success': True})
        elif item_type == 'et_nonrandom_feature':
            item = EnemyNonrandomFeature.objects.get(id=item_id)
            item.delete()
            return JsonResponse({'success': True})
        elif item_type == 'party_nonrandom_feature':
            item = PartyNonrandomFeature.objects.get(id=item_id)
            item.delete()
            return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
def get_feature_list_items(request, list_id):
    flist = AdditionalFeatureList.objects.get(id=list_id)
    output = []
    for item in flist.items:
        output.append({'id': item.id, 'name': item.name})
    return JsonResponse({'data': output})


@login_required
def submit(request, id):
    body = json.loads(request.body)
    value = body['value']
    object = body['object']
    parent_id = body.get('parent_id', None)
    logger = logging.getLogger(__name__)
    try:
        id = int(id)
        success = True
        message = ''
        original_value = None
        
        # Basics
        if object == 'et_name':
            et = EnemyTemplate.objects.get(id=id, owner=request.user)
            et.name = value
            et.save()
        elif object == 'et_namelist':
            et = EnemyTemplate.objects.get(id=id, owner=request.user)
            try:
                namelist = AdditionalFeatureList.objects.get(type='name', id=value)
            except AdditionalFeatureList.DoesNotExist:
                namelist = None
            et.namelist = namelist
            et.save()
        elif object == 'et_rank':
            et = EnemyTemplate.objects.get(id=id, owner=request.user)
            et.rank = int(value)
            et.save()
        elif object == 'et_cult_rank':
            et = EnemyTemplate.objects.get(id=id, owner=request.user)
            et.cult_rank = int(value)
            et.save()
        elif object == 'et_published':
            et = EnemyTemplate.objects.get(id=id, owner=request.user)
            et.published = to_bool(value)
            et.save()
        elif object == 'et_natural_armor':
            et = EnemyTemplate.objects.get(id=id, owner=request.user)
            et.natural_armor = to_bool(value)
            et.save()

        # Attributes
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
                
        # Skills
        elif object == 'et_skill_value':
            es = EnemySkill.objects.get(id=id)
            original_value = es.die_set
            try:
                value = es.set_value(value)
            except ValueError:
                success = False
                message = '%s is not a valid die value.' % value
        elif object == 'et_skill_include':
            es = EnemySkill.objects.get(id=id)
            es.include = to_bool(value)
            es.save()

        # Custom Skills
        elif object == 'et_custom_skill_value':
            cs = CustomSkill.objects.get(id=id)
            try:
                value = cs.set_value(value)
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

        # Spells
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
        elif object == 'et_mysticism_spell_amount':
            et = EnemyTemplate.objects.get(id=id, owner=request.user)
            et.mysticism_spell_amount = value
            et.save()
        elif object == 'et_spirit_amount':
            et = EnemyTemplate.objects.get(id=id, owner=request.user)
            et.spirit_amount = value
            et.save()
        elif object == 'et_spirit_prob':
            es = EnemySpirit.objects.get(id=id)
            try:
                es.probability = int(value)
                es.save()
            except ValueError:
                success = False
                message = 'Probability must be a number.'
        elif object == 'et_cult_amount':
            et = EnemyTemplate.objects.get(id=id, owner=request.user)
            et.cult_amount = value
            et.save()
        elif object == 'et_cult_prob':
            ec = EnemyCult.objects.get(id=id)
            try:
                ec.probability = int(value)
                ec.save()
            except ValueError:
                success = False
                message = 'Probability must be a number.'
            
        # Weapons and Combat Styles
        elif object == 'et_combat_style_name':
            cs = CombatStyle.objects.get(id=id)
            cs.name = value
            cs.save()
        elif object == 'et_combat_style_value':
            cs = CombatStyle.objects.get(id=id)
            try:
                cs.set_value(value)
            except:
                success = False
                message = 'Probability must be a number.'
                original_value = cs.die_set
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
        elif object == 'et_custom_weapon_range':
            cw = CustomWeapon.objects.get(id=id)
            cw.range = value
            cw.save()
        elif object == 'et_custom_weapon_type':
            cw = CustomWeapon.objects.get(id=id)
            cw.type = value
            cw.save()
        elif object == 'et_custom_weapon_damage_modifier':
            cw = CustomWeapon.objects.get(id=id)
            cw.damage_modifier = to_bool(value)
            cw.save()
        elif object == 'et_custom_weapon_natural_weapon':
            cw = CustomWeapon.objects.get(id=id)
            cw.natural_weapon = to_bool(value)
            cw.save()
        elif object == 'et_custom_weapon_ap_hp_as_per':
            cw = CustomWeapon.objects.get(id=id)
            cw.ap_hp_as_per = value
            cw.save()
        elif object == 'et_custom_weapon_special_effects':
            cw = CustomWeapon.objects.get(id=id)
            cw.special_effects = value
            cw.save()
            
        # Race
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
                Dice(value).roll()
                hl.hp_modifier = value
                hl.save()
            except ValueError:
                original_value = hl.hp_modifier
                success = False
                message = "HP Modifier must be a number or a valid die"
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
        elif object == 'race_discorporate':
            race = Race.objects.get(id=id, owner=request.user)
            race.discorporate = to_bool(value)
            race.save()
            
        # Party
        elif object == 'party_name':
            p = Party.objects.get(id=id, owner=request.user)
            p.name = value
            p.save()
        elif object == 'party_template_amount':
            p = Party.objects.get(id=parent_id, owner=request.user)
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
        elif object == 'party_notes':
            party = Party.objects.get(id=id, owner=request.user)
            party.notes = value
            party.save()
        elif object == 'party_newtag':
            p = Party.objects.get(id=id, owner=request.user)
            for tag in value.split(','):
                p.tags.add(tag.strip().capitalize())
        elif object == 'party_deltag':
            p = Party.objects.get(id=id, owner=request.user)
            p.tags.remove(value.capitalize())

        # Misc
        elif object == 'et_notes':
            et = EnemyTemplate.objects.get(id=id, owner=request.user)
            et.notes = value
            et.save()
        elif object == 'et_newtag':
            et = EnemyTemplate.objects.get(id=id, owner=request.user)
            for tag in value.split(','):
                et.tags.add(tag.strip().capitalize())
        elif object == 'et_deltag':
            et = EnemyTemplate.objects.get(id=id, owner=request.user)
            et.tags.remove(value.capitalize())
        elif object == 'et_feature_prob':
            afl = EnemyAdditionalFeatureList.objects.get(id=id, enemy_template__owner=request.user)
            try:
                afl.set_probability(value)
            except:
                original_value = afl.probability
                success = False
        elif object == 'party_feature_prob':
            afl = PartyAdditionalFeatureList.objects.get(id=id, party__owner=request.user)
            try:
                afl.set_probability(value)
            except:
                original_value = afl.probability
                success = False
            
        return JsonResponse({'success': success, 'message': message,
                           'value': value, 'original_value': original_value})
    except Exception as e:
        logger.error(str(e))
        return JsonResponse({'error': str(e)})


def change_template(request):
    """ Changes the name of the generated enemy, in the given html
        Input: html_file    - name of the html file to modify
               id           - id of the html element to modify
               value        - new value
    """
    body = json.loads(request.body)
    html_file = html.unescape(settings.TEMP + os.path.sep + body['html_file'])
    id = body['id']
    value = body['value']
    with open(html_file, 'r') as ff:
        soup = BeautifulSoup(ff, 'html.parser')
    span_tag = soup.find('span', {'id': id})
    klasses = ' '.join(span_tag['class'])
    new_tag = BeautifulSoup('<span id="%s" class="%s">%s</span>' % (id, klasses, value), 'html.parser').span
    soup.find('span', {'id': id}).replaceWith(new_tag)
    with open(html_file, 'w') as ff:
        ff.write(soup.prettify())
    return JsonResponse({'html_file': html_file})


def toggle_star(request, et_id):
    if request.user.is_authenticated:
        EnemyTemplate.objects.get(id=et_id).toggle_star(request.user)
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False})


def search(request):
    params = request.GET
    templs = EnemyTemplate.search(params.get('string', ''), request.user, params.getlist('rank_filter[]', []), params.getlist('cult_rank_filter[]', []))
    templates = [et.summary_dict(request.user) for et in templs]
    return JsonResponse({'results': templates, 'success': True})


def get_weapons(request, cs_id):
    cs = CombatStyle.objects.get(id=cs_id)
    cs.enemy_template.weapon_filter = request.GET['filter']
    cs.enemy_template.save()
    context = {'weapons': weapons(cs), 'success': True}
    return JsonResponse(context)
