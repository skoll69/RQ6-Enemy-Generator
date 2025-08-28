# pylint: disable=no-member

from enemygen.models import Ruleset, EnemyTemplate, Race
from enemygen.models import SpellAbstract, EnemySpell, CustomSpell, ChangeLog
from enemygen.models import Weapon, CombatStyle, EnemyWeapon, CustomWeapon, Party, AdditionalFeatureList, EnemySkill

from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.db.models import Q, Sum
from django.conf import settings

from bs4 import BeautifulSoup
from tempfile import NamedTemporaryFile
import os
import random
import datetime
import json
try:
    from weasyprint import HTML, CSS
    from PIL import Image, ImageChops
except:
    pass

def get_filter(request):
    return request.session.get('filter', None)


def get_party_filter(request):
    return request.session.get('party_filter', None)


def get_ruleset(request):
    return Ruleset.objects.get(id=request.session.get('ruleset_id', 1))


def get_context(request):
    context = {'filter': get_filter(request),
               'party_filter': get_party_filter(request),
               'generated': _get_generated_amount(),
               'request': request,
               'all_et_tags': sorted(list(EnemyTemplate.tags.all()), key=lambda x: x.name),
               'all_party_tags': sorted(list(Party.tags.all()), key=lambda x: x.name)
               }
    if (datetime.date.today() - ChangeLog.objects.all().reverse()[0].publish_date).days < 14:
        context['recent_changes'] = True
    return context


def get_et_context(et):
    context = {'et': et,
               'theism_spells': spell_list('theism', et),
               'folk_spells': spell_list('folk', et),
               'sorcery_spells': spell_list('sorcery', et),
               'mysticism_spells': spell_list('mysticism', et),
               'combat_styles': combat_styles(et),
               'spirit_options': spirit_options(),
               'cult_options': cult_options(),
               'additional_feature_lists': AdditionalFeatureList.objects.filter(type='enemy_feature'),
               'namelists': AdditionalFeatureList.objects.filter(type='name'),
            }
    return context


def get_party_templates(filtr=None):
    if filtr and filtr != 'None':
        parties = list(Party.objects.filter(tags__name__in=[filtr, ], published=True))
    else:
        parties = list(Party.objects.filter(published=True))
    return parties


def get_party_context(party):
    templates = EnemyTemplate.objects.filter(Q(published=True) | Q(owner=party.owner)).exclude(race__name='Cult')
    context = {'party': party,
               'templates': templates.order_by('name'),
               'all_party_tags': sorted(list(Party.tags.all()), key=lambda x: x.name),
               'additional_feature_lists': AdditionalFeatureList.objects.filter(type='party_feature')}
    return context


def get_enemy_templates(filtr, user):
    published_templates = EnemyTemplate.objects.filter(published=True).order_by('rank').exclude(race__name='Cult').select_related('race')
    if filtr and filtr not in ('None', 'Starred'):
        templates = list(published_templates.filter(tags__name__in=[filtr, ]))
    elif filtr == 'Starred':
        templates = EnemyTemplate.get_starred(user)
    else:
        templates = list(published_templates)
    if user.is_authenticated:
        # Add the unpublished templates of the logged-in user
        unpubl = EnemyTemplate.objects.filter(published=False, owner=user).order_by('rank').exclude(race__name='Cult').select_related('race')
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
            et = EnemyTemplate.objects.get(id=enemy_template_id)
        except EnemyTemplate.DoesNotExist:
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
        for i in range(amount):
            enemies.append(et.generate(i+1, increment))
    return enemies


def get_enemies_lucky(request):
    """ Returns a six instances of a randomly selected enemy based on the current filter """
    filtr = get_filter(request)
    if filtr and filtr != 'None':
        templates = EnemyTemplate.objects.filter(tags__name__in=[filtr, ], published=True)
        if not templates:
            templates = EnemyTemplate.objects.filter(published=True)
    else:
        templates = EnemyTemplate.objects.filter(published=True)
    index = random.randint(0, len(templates)-1) 
    enemies = []
    for i in range(6):
        enemies.append(templates[index].generate(i+1))
    return enemies


def get_random_party(filtr=None):
    if filtr and filtr != 'None':
        parties = Party.objects.filter(tags__name__in=[filtr, ], published=True)
    else:
        parties = Party.objects.filter(published=True)
    index = random.randint(0, len(parties)-1)
    return parties[index]


def get_generated_party(party):
    context = {'party': party,
               'enemies': _get_party_enemies(party),
               'party_additional_features': party.get_random_additional_features()}
    nonrandom_feature = [item.feature for item in party.nonrandom_features]
    context['party_additional_features'].extend(nonrandom_feature)
    return context


def _get_party_enemies(party):
    enemies = []
    for ttp in party.template_specs:
        et = ttp.template
        amount = ttp.get_amount()
        et.increment_used()
        for i in range(amount):
            enemies.append(et.generate(i+1, True))
    return enemies


def _get_generated_amount():
    return EnemyTemplate.objects.aggregate(Sum('generated'))['generated__sum']


def spell_list(spell_type, et):
    """ Returns the list of the given type of spells for the given EnemyTemplate """
    output = []
    found = []
    for spell in EnemySpell.objects.filter(enemy_template=et, spell__type=spell_type).select_related('spell'):
        output.append({'id': spell.spell.id, 'name': spell.spell.name, 'probability': spell.probability, 'detail_text': spell.detail, 'detail': spell.spell.detail })
        found.append(spell.spell.id)
    for spell in SpellAbstract.objects.filter(type=spell_type).exclude(id__in=found):
        output.append({'id': spell.id, 'name': spell.name, 'probability': 0, 'detail_text': spell.default_detail, 'detail': spell.detail})
    output.sort(key=lambda x: x['name'])
    for spell in CustomSpell.objects.filter(enemy_template=et, type=spell_type):
        sp = {'id': spell.id, 'name': spell.name, 'probability': spell.probability, 'custom': True}
        output.append(sp)
    return output


def combat_styles(et):
    """ Returns a list of combat styles, that contains a list of weapons. The weaponlist contains
        all weapons in the system. The weapons, that have been selected to the CombatStyle (by
        assigning a probability) have also their probability listed.
    """
    output = []
    for cs in CombatStyle.objects.filter(enemy_template=et):
        cs_out = {'id': cs.id, 'name': cs.name, 'die_set': cs.die_set,
                  'one_h_amount': cs.one_h_amount, 'two_h_amount': cs.two_h_amount,
                  'ranged_amount': cs.ranged_amount, 'shield_amount': cs.shield_amount,
                  '1h_melee': [], '2h_melee': [], 'ranged': [], 'shield': [], 'customs': []}
        cs_out.update(weapons(cs))
        # Append Custom weapons
        for tipe in ('1h-melee', '2h-melee', 'ranged', 'shield'):
            for cw in CustomWeapon.objects.filter(combat_style=cs, type=tipe):
                cs_out['customs'].append(cw)
        output.append(cs_out)
    return output


def weapons(combat_style):
    out = {'1h_melee': [], '2h_melee': [], 'ranged': [], 'shield': []}
    filtr = combat_style.enemy_template.weapon_filter if combat_style.enemy_template.weapon_filter else 'Standard'
    prev_weapon = None
    for tipe in ('1h-melee', '2h-melee', 'ranged', 'shield'):
        typeout = tipe.replace('-', '_')  # '-' is not allowed in the lookup string in Django template
        weaponlist = Weapon.objects.filter(type=tipe)
        if filtr != 'All':
            weaponlist = weaponlist.filter(tags__name=filtr)
        for weapon in weaponlist:
            if prev_weapon and weapon.name == prev_weapon.name:
                weapon.name = '%s (%s)' % (weapon.name, ', '.join(weapon.tags.names()))
                out[typeout][-1]['name'] = '%s (%s)' % (prev_weapon.name, ', '.join(prev_weapon.tags.names()))
            try:
                ew = EnemyWeapon.objects.get(weapon=weapon, combat_style=combat_style)
                prob = ew.probability
            except EnemyWeapon.DoesNotExist:
                prob = 0
            out[typeout].append({'id': weapon.id, 'name': weapon.name, 'probability': prob})
            prev_weapon = weapon
    return out


def spirit_options():
    return EnemyTemplate.objects.filter(race__discorporate=True, published=True)


def cult_options():
    return EnemyTemplate.objects.filter(race__name='Cult', published=True)


def is_race_admin(user):
    return bool(user.groups.filter(name='race_admin').count())


def is_superuser(user):
    return bool(user.groups.filter(name='superuser').count())


def get_statistics():
    templates = EnemyTemplate.objects.filter(published=True).exclude(race__name='Cult')
    cults = EnemyTemplate.objects.filter(published=True, race__name='Cult')
    races = Race.objects.filter(published=True)
    races_stats = list({'name': r.name, 'id': r.id, 'template_amount': len(r.templates)} for r in races if r.templates)
    races_stats = sorted(races_stats, reverse=True, key=lambda r: r['template_amount'])
    users = list({'name': u.username, 'template_amount': len(templates.filter(owner=u))} for u in User.objects.all())
    users = sorted(users, reverse=True, key=lambda item: item['template_amount'])
    users = list(user for user in users if user['template_amount'] > 0)
    clts = list({'name': c.name, 'id': c.id, 'rank': c.get_cult_rank_display(), 'rank_int': c.cult_rank} for c in cults)
    clts = sorted(clts, reverse=False, key=lambda et: et['name'])

    output = {'templates': templates.filter(generated__gt=29).order_by('-generated'),
              'races': races_stats,
              'users': users,
              'cults': clts,
              'total_published_templates': templates.count(),
              'total_published_races': races.count(),
              'total_published_cults': cults.count(),
              'common_cults': cults.filter(cult_rank=1).count(),
              'dedicated_cults': cults.filter(cult_rank=2).count(),
              'proven_cults': cults.filter(cult_rank=3).count(),
              'overseer_cults': cults.filter(cult_rank=4).count(),
              'leader_cults': cults.filter(cult_rank=5).count()}
    return output


def save_as_html(context, template_name):
    """ Renders the generated enemies to html and saves to disk, so that it can be converted to PDF later """
    rendered = render_to_string(template_name, context)
    prefix = _get_html_prefix(context)
    htmlfile = NamedTemporaryFile(mode='w', prefix=prefix, suffix='.html', dir=settings.TEMP, delete=False)
    htmlfile.write(rendered)
    htmlfile.close()
    return os.path.basename(htmlfile.name)


def _get_html_prefix(context):
    party = context.get('party', None)
    if party:
        prefix = 'rq_%s_' % party.name
    else:
        # noinspection PyBroadException
        try:
            prefix = 'rq_%s_' % context['enemies'][0].name.replace('_1', 's').replace('/', '_')
        except:
            prefix = 'rq_'
    return prefix.replace(' ', '_').replace("'", '').replace('"', '')


def generate_pdf(html_path):
    """ Generates a PDF based on the given html file """
    html_path = os.path.join(settings.TEMP, html_path)
    pdf_path = html_path.replace('.html', '.pdf')
    HTML(html_path).write_pdf(pdf_path)
    return pdf_path


def generate_pngs(html_path):
    """ Generates png-images out of the generated_html """
    with open(os.path.join(settings.TEMP, html_path).encode('utf-8'), 'r') as ff:
        soup = BeautifulSoup(ff, 'html.parser')
    enemies = soup.find_all('div', {'class': 'enemy_container'})
    container = soup.find('div', {'id': 'enemies'})
    pngs = []
    for enemy in enemies:
        container.clear()
        container.append(enemy)
        htmlfile = NamedTemporaryFile(mode='w', suffix='.html', dir=settings.TEMP, delete=False)
        htmlfile.write(soup.prettify())
        htmlfile.close()
        png_name = htmlfile.name.replace('.html', '.png')
        HTML(htmlfile.name).write_png(png_name, stylesheets=[CSS(string='@media print{body, td, th{font-size: 11px !important;}}')])
        _trim(png_name)
        pngs.append(png_name)
    return pngs


def as_json(enemies):
    """ Input: A list of generated enemies. Output: The enemies as a json string """
    out = []
    for e in enemies:
        out.append(enemy_as_json(e))
    return json.dumps(out)

def enemy_as_json(e):
    # Normalize cult_rank to a numeric value; default to 0 when missing/None
    cult_rank_val = getattr(e, 'cult_rank', None)
    try:
        # Handle common string cases like 'None' or ''
        if cult_rank_val in (None, ''):
            cult_rank_num = 0
        elif isinstance(cult_rank_val, str) and cult_rank_val.lower() == 'none':
            cult_rank_num = 0
        else:
            cult_rank_num = int(cult_rank_val)
    except Exception:
        cult_rank_num = 0

    out = {
        'name': e.name,
        'cult_rank': cult_rank_num,
        'stats': [{s['name']: s['value']} for s in e.stats_list],
        'skills': [{s['name']: s['value']} for s in e.skills],
        'folk_spells': [s.name for s in e.folk_spells],
        'theism_spells': [s.name for s in e.theism_spells],
        'sorcery_spells': [s.name for s in e.sorcery_spells],
        'mysticism_spells': [s.name for s in e.mysticism_spells],
        'hit_locations': [{'name': hl['name'], 'range': hl['range'], 'hp': hl['hp'], 'ap': hl['ap']} for hl in e.hit_locations],
        'combat_styles': [{'weapons': [{'name': w.name, 'damage': w.damage, 'ap': w.ap, 'hp': w.hp, 'size': w.size,
                                        'add_damage_modifier': w.damage_modifier, 'reach': w.reach,
                                        'effects': w.special_effects, 'range': w.range, 'type': w.type} for w in cs['weapons']],
                           'name': cs['name'], 'value': cs['value'], } for cs in e.combat_styles],
        'attributes': e.attributes,
        'notes': e.notes,
        'features': ['%s: %s' % (f.feature_list.name, f.name) for f in e.additional_features],
        'cults': [c.name for c in e.cults],
        'spirits': [enemy_as_json(s) for s in e.spirits],
    }
    # Ensure all defined EnemySkill names for the template are present in JSON, even if not included for rolling
    try:
        expected_skill_names = list(EnemySkill.objects.filter(enemy_template=e.et).select_related('skill').values_list('skill__name', flat=True))
        present_skill_names = {list(d.keys())[0] for d in out['skills']}
        for sk_name in expected_skill_names:
            if sk_name not in present_skill_names:
                out['skills'].append({sk_name: 0})  # default value if not rolled/included
    except Exception:
        # If anything goes wrong, do not block JSON generation
        pass

    if hasattr(e, 'natural_armor'):
        out['natural_armor'] = e.natural_armor
    return out

def _trim(image_path):
    """ Removes the border from the given image """
    im = Image.open(image_path)
    im = im.crop(im.getbbox())  # Trims the transparent border if any
    bg = Image.new(im.mode, im.size, im.getpixel((0,0)))  # 3rd argument is the color of the first pixel
    diff = ImageChops.difference(im, bg)
    bbox = diff.getbbox()
    im = im.crop(bbox)
    im.save(image_path)
