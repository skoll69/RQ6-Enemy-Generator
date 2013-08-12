from django.utils import simplejson
from dajaxice.decorators import dajaxice_register
from enemygen.models import EnemyStat, EnemySkill, EnemyTemplate, Ruleset, StatAbstract
from enemygen.models import SpellAbstract, SkillAbstract, EnemySpell, EnemyHitLocation
from enemygen.models import CombatStyle, Weapon, Setting, CustomSpell

from enemygen.enemygen_lib import to_bool

@dajaxice_register
def add_custom_spell(request, et_id, type):
    try:
        CustomSpell.create(et_id, type)
        return simplejson.dumps({'success': True})
    except Exception as e:
        return simplejson.dumps({'error': str(e)})
    
@dajaxice_register
def submit(request, value, id, object, parent_id=None, extra={}):
    try:
        id = int(id)
        success = True
        message = ''
        original_value = None
        if object == 'et_stat_value':
            es = EnemyStat.objects.get(id=id)
            original_value = es.die_set
            try:
                es.set_value(value)
            except ValueError:
                success = False
                message = '%s is not a valid die value.' % value
        elif object == 'et_skill_value':
            es = EnemySkill.objects.get(id=id)
            original_value = es.die_set
            try:
                es.set_value(value)
            except ValueError:
                success = False
                message = '%s is not a valid die value.' % value
        elif object == 'et_skill_include':
            es = EnemySkill.objects.get(id=id)
            es.include = to_bool(value)
            es.save()
        elif object == 'et_spell_prob':
            sa = SpellAbstract.objects.get(id=id)
            et = EnemyTemplate.objects.get(id=parent_id, owner=request.user)
            try:
                es = EnemySpell.objects.get(spell=sa, enemy_template=et)
            except:
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
        #elif object == 'stat_name':
        #    stat = StatAbstract.objects.get(id=id)
        #    stat.name = value
        #    stat.save()
        #elif object == 'spell_name':
        #    spell = SpellAbstract.objects.get(id=id)
        #    spell.name = value
        #    spell.save()
        #elif object == 'skill_name':
        #    skill = SkillAbstract.objects.get(id=id)
        #    skill.name = value
        #    skill.save()
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
        elif object == 'et_hl_armor':
            ehl = EnemyHitLocation.objects.get(id=id)
            try:
                ehl.set_armor(value)
            except ValueError:
                original_value = ehl.armor
                success = False
                message = "Not a valid dice set"
        elif object == 'et_combat_style_name':
            cs = CombatStyle.objects.get(id=id)
            cs.name = value
            cs.save()
        elif object == 'et_combat_style_value':
            cs = CombatStyle.objects.get(id=id)
            cs.die_set = value
            cs.save()
        elif object == 'et_weapon_include':
            cs = CombatStyle.objects.get(id=int(parent_id))
            weapon = Weapon.objects.get(id=id)
            if to_bool(value):
                cs.weapon_options.add(weapon)
            else:
                cs.weapon_options.remove(weapon)
            cs.save()
        elif object == 'et_published':
            et = EnemyTemplate.objects.get(id=id, owner=request.user)
            et.published = to_bool(value)
            et.save()
        return simplejson.dumps({'success': success, 'message': message, 'original_value': original_value})
    except Exception as e:
        return simplejson.dumps({'error': str(e)})
