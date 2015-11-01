from mw import models as m
from enemygen.views_lib import get_filter, get_party_filter

from django.contrib.auth.models import User
from django.db.models import Q

import random
import datetime


def get_context(request):
    context = {'filter': get_filter(request),
               'party_filter': get_party_filter(request),
               'generated': _get_generated_amount(),
               'request': request,
               'all_et_tags': sorted(list(m.MWEnemyTemplate.tags.all()), key=lambda x: x.name),
               'all_party_tags': sorted(list(m.MWParty.tags.all()), key=lambda x: x.name)}
    if m.ChangeLog.objects.all().count() and (datetime.date.today() - m.ChangeLog.objects.all().reverse()[0].publish_date).days < 14:
        context['recent_changes'] = True
    return context


def get_et_context(et):
    context = {'et': et,
               'spells': spell_list(et),
               'combat_styles': combat_styles(et),
               'namelists': m.AdditionalFeatureList.objects.filter(type='name')}
    return context


def get_party_templates(filtr=None):
    if filtr and filtr != 'None':
        parties = list(m.MWParty.objects.filter(tags__name__in=[filtr, ], published=True))
    else:
        parties = list(m.MWParty.objects.filter(published=True))
    return parties


def get_party_context(party):
    templates = m.MWEnemyTemplate.objects.filter(Q(published=True) | Q(owner=party.owner))
    context = {'party': party,
               'templates': templates.order_by('name'),
               'all_party_tags': sorted(list(m.MWParty.tags.all()), key=lambda x: x.name), }
    return context


def get_enemy_templates(filtr, user):
    published_templates = m.MWEnemyTemplate.objects.filter(published=True).order_by('rank')
    if filtr and filtr not in ('None', 'Starred'):
        templates = list(published_templates.filter(tags__name__in=[filtr, ]))
    elif filtr == 'Starred':
        templates = m.MWEnemyTemplate.get_starred(user)
    else:
        templates = list(published_templates)
    if user.is_authenticated():
        # Add the unpublished templates of the logged-in user
        unpubl = m.MWEnemyTemplate.objects.filter(published=False, owner=user).order_by('rank')
        if filtr:
            templates.extend(list(unpubl.filter(tags__name__in=[filtr, ])))
        else:
            templates.extend(list(unpubl))
        # Add stars (We can't call is_starred with the user parameter in Django template)
        for et in templates:
            et.starred = et.is_starred(user)
    return templates


def determine_enemies(post):
    """ Determines the EnemyTemplates to be used and the amounts to be generated based on the POST data
        Output is a list of tuples of (EnemyTemplate, amount)
    """
    index = []
    for key, amount in post.items():
        if 'enemy_template_id_' not in key:
            continue
        enemy_template_id = int(key.replace('enemy_template_id_', ''))
        try:
            et = m.MWEnemyTemplate.objects.get(id=enemy_template_id)
        except m.MWEnemyTemplate.DoesNotExist:
            continue
        try:
            amount = int(amount)
        except ValueError:
            continue
        amount = min(amount, 40)
        if amount > 0:
            index.append((et, amount))
    index.sort(key=lambda tup: tup[0].rank, reverse=True)
    return index


def get_enemies(index, increment):
    """ Generates the enemies.
        Input: a list of tuples of (EnemyTemplate, amount)
    """
    enemies = []
    for et, amount in index:
        if increment:
            et.increment_used()
        for i in xrange(amount):
            enemies.append(et.generate(i+1, increment))
    return enemies


def get_enemies_lucky(request):
    """ Returns a six instances of a randomly selected enemy based on the current filter """
    filtr = get_filter(request)
    if filtr and filtr != 'None':
        templates = m.MWEnemyTemplate.objects.filter(tags__name__in=[filtr, ], published=True)
    else:
        templates = m.MWEnemyTemplate.objects.filter(published=True)
    index = random.randint(0, len(templates)-1) 
    enemies = []
    for i in xrange(6):
        enemies.append(templates[index].generate(i+1))
    return enemies


def get_random_party(filtr=None):
    if filtr and filtr != 'None':
        parties = m.MWParty.objects.filter(tags__name__in=[filtr, ], published=True)
    else:
        parties = m.MWParty.objects.filter(published=True)
    index = random.randint(0, len(parties)-1)
    return parties[index]


def get_generated_party(party):
    context = {'party': party,
               'enemies': _get_party_enemies(party),}
    return context


def _get_party_enemies(party):
    enemies = []
    for ttp in party.template_specs:
        et = ttp.template
        amount = ttp.get_amount()
        et.increment_used()
        for i in xrange(amount):
            enemies.append(et.generate(i+1, True))
    return enemies


def _get_generated_amount():
    n = 0
    for et in m.MWEnemyTemplate.objects.all():
        n += et.generated
    return n


def spell_list(et):
    """ Returns the list of the given type of spells for the given EnemyTemplate """
    output = []
    for spell in m.SpellAbstract.objects.all():
        try:
            es = m.EnemySpell.objects.get(spell=spell, enemy_template=et)
            prob = es.probability
            detail_text = es.detail
        except m.EnemySpell.DoesNotExist:
            prob = 0
            detail_text = spell.default_detail
        sp = {'id': spell.id, 'name': spell.name, 'probability': prob, 'detail_text': detail_text,
              'detail': spell.detail}
        output.append(sp)
    for spell in m.CustomSpell.objects.filter(enemy_template=et):
        sp = {'id': spell.id, 'name': spell.name, 'probability': spell.probability, 'custom': True}
        output.append(sp)
    return output


def combat_styles(et):
    """ Returns a list of combat styles, that contains a list of weapons. The weaponlist contains
        all weapons in the system. The weapons, that have been selected to the CombatStyle (by
        assigning a probability) have also their probability listed.
    """
    output = []
    for cs in m.CombatStyle.objects.filter(enemy_template=et):
        cs_out = {'id': cs.id, 'one_h_amount': cs.one_h_amount, 'two_h_amount': cs.two_h_amount,
                  'ranged_amount': cs.ranged_amount, 'shield_amount': cs.shield_amount,
                  '1h_melee': [], '2h_melee': [], 'ranged': [], 'shield': [], 'customs': []}
        cs_out.update(weapons(cs))
        # Append Custom weapons
        for tipe in ('1h-melee', '2h-melee', 'ranged', 'shield'):
            for cw in m.CustomWeapon.objects.filter(combat_style=cs, type=tipe):
                cs_out['customs'].append(cw)
        output.append(cs_out)
    return output


def weapons(combat_style):
    out = {'1h_melee': [], '2h_melee': [], 'ranged': [], 'shield': []}
    for tipe in ('1h-melee', '2h-melee', 'ranged', 'shield'):
        typeout = tipe.replace('-', '_')  # '-' is not allowed in the lookup string in Django template
        weaponlist = m.Weapon.objects.filter(type=tipe)
        for weapon in weaponlist:
            try:
                ew = m.EnemyWeapon.objects.get(weapon=weapon, combat_style=combat_style)
                prob = ew.probability
                skill = ew.die_set
            except m.EnemyWeapon.DoesNotExist:
                prob = 0
                skill = weapon.base_skill
            out[typeout].append({'id': weapon.id, 'name': weapon.name, 'probability': prob, 'die_set': skill})
    return out


def get_statistics():
    templates = m.MWEnemyTemplate.objects.filter(published=True)
    users = list({'name': u.username, 'template_amount': len(templates.filter(owner=u))} for u in User.objects.all())
    users = sorted(users, reverse=True, key=lambda item: item['template_amount'])
    users = list(user for user in users if user['template_amount'] > 0)

    output = {'templates': templates.filter(generated__gt=29).order_by('-generated'),
              'users': users,
              'total_published_templates': templates.count()}
    return output
