from enemygen.models import Ruleset, EnemyTemplate, Race, Weapon
from enemygen.models import SpellAbstract, EnemySpell, CustomSpell
from enemygen.models import Weapon, CombatStyle, EnemyWeapon, CustomWeapon, Party, AdditionalFeatureList

from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.db.models import Q

from bs4 import BeautifulSoup
from tempfile import NamedTemporaryFile
import os
import random

def get_filter(request):
    return request.session.get('filter', None)
    
def get_party_filter(request):
    return request.session.get('party_filter', None)
    
def get_ruleset(request):
    return Ruleset.objects.get(id=request.session.get('ruleset_id', 1))

def get_context(request):
    context = {}
    context['filter'] = get_filter(request)
    context['party_filter'] = get_party_filter(request)
    context['generated'] = _get_generated_amount()
    context['request'] = request
    context['all_et_tags'] = sorted(list(EnemyTemplate.tags.all()), key=lambda x: x.name)
    context['all_party_tags'] = sorted(list(Party.tags.all()), key=lambda x: x.name)
    return context
    
def get_et_context(et):
    context = {}
    context['et'] = et
    context['weapons'] = {}
    context['weapons']['1h'] = Weapon.objects.filter(type='1h-melee')
    context['weapons']['2h'] = Weapon.objects.filter(type='2h-melee')
    context['weapons']['ranged'] = Weapon.objects.filter(type='ranged')
    context['weapons']['shields'] = Weapon.objects.filter(type='shield')
    context['theism_spells'] = spell_list('theism', et)
    context['folk_spells'] = spell_list('folk', et)
    context['sorcery_spells'] = spell_list('sorcery', et)
    context['mysticism_spells'] = spell_list('mysticism', et)
    context['combat_styles'] = combat_styles(et)
    context['spirit_options'] = spirit_options()
    context['cult_options'] = cult_options()
    context['additional_feature_lists'] = AdditionalFeatureList.objects.filter(type='enemy_feature')
    context['namelists'] = AdditionalFeatureList.objects.filter(type='name')
    return context

def get_party_templates(filter=None):
    if filter and filter != 'None':
        parties = list(Party.objects.filter(tags__name__in=[filter,], published=True))
    else:
        parties = list(Party.objects.filter(published=True))
    return parties
    
def get_party_context(party):
    context = {}
    context['party'] = party
    context['templates'] = EnemyTemplate.objects.filter(Q(published=True) | Q(owner=party.owner)).exclude(race__name='Cult').order_by('name')
    context['all_party_tags'] = sorted(list(Party.tags.all()), key=lambda x: x.name)
    context['additional_feature_lists'] = AdditionalFeatureList.objects.filter(type='party_feature')
    return context
    
def get_enemy_templates(filter, user):
    published_templates = EnemyTemplate.objects.filter(published=True).order_by('rank').exclude(race__name='Cult')
    if filter and filter not in ('None', 'Starred'):
        templates = list(published_templates.filter(tags__name__in=[filter,]))
    elif filter == 'Starred':
        templates = EnemyTemplate.get_starred(user)
    else:
        templates = list(published_templates)
    if user.is_authenticated():
        # Add the unpublished templates of the logged-in user
        unpublished_templates = EnemyTemplate.objects.filter(published=False, owner=user).order_by('rank').exclude(race__name='Cult')
        if filter:
            templates.extend(list(unpublished_templates.filter(tags__name__in=[filter,])))
        else:
            templates.extend(list(unpublished_templates))
        # Add stars (We can't call is_starred with the user parameter in Django template)
        for et in templates:
            et.starred = et.is_starred(user)
    return templates
    
def get_enemies(request):
    enemies = []
    index = []
    increment = False if request.POST.get('dont_increment') else True   # Increment the number of enemies generated?
    for key, amount in request.POST.items():
        if not 'enemy_template_id_' in key: continue
        enemy_template_id = int(key.replace('enemy_template_id_', ''))
        try:
            et = EnemyTemplate.objects.get(id=enemy_template_id)
        except EnemyTemplate.DoesNotExist:
            continue
        try:
            amount = int(amount)
        except ValueError:
            continue
        if amount > 40: amount = 40
        index.append((et, amount))
    index.sort(key=lambda tup: tup[0].rank, reverse=True)
    for et, amount in index:
        if increment:
            et.increment_used()
        for i in xrange(amount):
            enemies.append(et.generate(i+1, increment))
    return enemies
    
def get_enemies_lucky(request):
    ''' Returns a four instances of a randomly selected enemy based on the current filter '''
    filter = get_filter(request)
    if filter and filter != 'None':
        templates = EnemyTemplate.objects.filter(tags__name__in=[filter,], published=True)
    else:
        templates = EnemyTemplate.objects.filter(published=True)
    index = random.randint(0, len(templates)-1) 
    enemies = []
    for i in xrange(6):
        enemies.append(templates[index].generate(i+1))
    return enemies
    
def get_random_party(filter=None):
    if filter and filter != 'None':
        parties = Party.objects.filter(tags__name__in=[filter,], published=True)
    else:
        parties = Party.objects.filter(published=True)
    index = random.randint(0, len(parties)-1)
    return parties[index]
    
def get_generated_party(party):
    context = {}
    context['party'] = party
    context['enemies'] = _get_party_enemies(party)
    context['party_additional_features'] = party.get_random_additional_features()
    nonrandom_feature = [item.feature for item in party.nonrandom_features]
    context['party_additional_features'].extend(nonrandom_feature)
    return context
    
def _get_party_enemies(party):
    enemies = []
    for ttp in party.template_specs:
        et = ttp.template
        amount = ttp.get_amount()
        et.increment_used()
        for i in xrange(amount):
            enemies.append(et.generate(i+1))
    return enemies
    

def _get_generated_amount():
    n = 0
    for et in EnemyTemplate.objects.all():
        n += et.generated
    return n
    
def spell_list(type, et):
    ''' Returns the list of the given type of spells for the given EnemyTemplate '''
    output = []
    for spell in SpellAbstract.objects.filter(type=type):
        try:
            es = EnemySpell.objects.get(spell=spell, enemy_template=et)
            prob = es.probability
            detail_text = es.detail
        except EnemySpell.DoesNotExist:
            prob = 0
            detail_text = spell.default_detail
        sp = {'id': spell.id, 'name': spell.name, 'probability': prob, 'detail_text': detail_text}
        sp['detail'] = spell.detail
        output.append(sp)
    for spell in CustomSpell.objects.filter(enemy_template=et, type=type):
        sp = {'id': spell.id, 'name': spell.name, 'probability': spell.probability, 'custom': True}
        output.append(sp)
    return output
    
def combat_styles(et):
    ''' Returns a list of combat styles, that contains a list of weapons. The weaponlist contains
        all weapons in the system. The weapons, that have been selected to the CombatStyle (by
        assigning a probability) have also their probability listed.
    '''
    output = []
    for cs in CombatStyle.objects.filter(enemy_template=et):
        cs_out = {'id': cs.id, 'name': cs.name, 'die_set': cs.die_set,
                  'one_h_amount': cs.one_h_amount ,'two_h_amount': cs.two_h_amount,
                  'ranged_amount': cs.ranged_amount,'shield_amount': cs.shield_amount,
                  '1h_melee': [], '2h_melee': [], 'ranged': [], 'shield': [], 'customs': []}
        for type in ('1h-melee', '2h-melee', 'ranged', 'shield'):
            typeout = type.replace('-', '_') # '-' is not allowed in the lookup string in Django template
            for weapon in Weapon.objects.filter(type=type):
                try:
                    ew = EnemyWeapon.objects.get(weapon=weapon, combat_style=cs)
                    prob = ew.probability
                except EnemyWeapon.DoesNotExist:
                    prob = 0
                cs_out[typeout].append({'id': weapon.id, 'name': weapon.name, 'probability': prob})
            # Append Custom weapons
            for cw in CustomWeapon.objects.filter(combat_style=cs, type=type):
                cs_out['customs'].append(cw)
        output.append(cs_out)
    return output
    
def spirit_options():
    return EnemyTemplate.objects.filter(race__discorporate=True, published=True)
    
def cult_options():
    return EnemyTemplate.objects.filter(race__name='Cult', published=True)
    
def is_race_admin(user):
    return bool(user.groups.filter(name='race_admin').count())
    
def is_superuser(user):
    return bool(user.groups.filter(name='superuser').count())
    
def get_statistics():
    output = {}
    
    templates = list((et.name, et.generated, et.id) for et in EnemyTemplate.objects.filter(published=True).exclude(race__name='Cult'))
    templates = sorted(templates, reverse=True, key=lambda et: et[1])
    templates_out = []
    for et in templates:
        if et[1] > 9:
            templates_out.append({'name': et[0], 'generated': et[1], 'id': et[2]})
    output['templates'] = templates_out
    
    races = list((r.name, r.id, len(r.templates)) for r in Race.objects.filter(published=True))
    races = sorted(races, reverse=True, key=lambda r: r[2])
    races_out = []
    for r in races:
        races_out.append({'name': r[0], 'id': r[1], 'template_amount': r[2]})
    output['races'] = races_out
    
    users = list((u.username, len(EnemyTemplate.objects.filter(owner=u, published=True))) for u in User.objects.all())
    users = sorted(users, reverse=True, key=lambda tup: tup[1])
    users_out = []
    for u in users:
        if u[1] > 2:
            users_out.append({'name': u[0], 'template_amount': u[1]})
    output['users'] = users_out
    
    cults = EnemyTemplate.objects.filter(published=True, race__name='Cult')
    cults = list({'name': et.name, 'id': et.id, 'rank': et.get_cult_rank_display(), 'rank_int': et.cult_rank} for et in cults)
    cults = sorted(cults, reverse=False, key=lambda et: et['name'])
    cults_out = cults
    output['cults'] = cults_out
    
    output['total_published_templates'] = EnemyTemplate.objects.filter(published=True).exclude(race__name='Cult').count()
    output['total_published_races'] = Race.objects.filter(published=True).count()
    output['total_published_cults'] = EnemyTemplate.objects.filter(published=True, race__name='Cult').count()
    output['common_cults'] = EnemyTemplate.objects.filter(published=True, race__name='Cult', cult_rank=1).count()
    output['dedicated_cults'] = EnemyTemplate.objects.filter(published=True, race__name='Cult', cult_rank=2).count()
    output['proven_cults'] = EnemyTemplate.objects.filter(published=True, race__name='Cult', cult_rank=3).count()
    output['overseer_cults'] = EnemyTemplate.objects.filter(published=True, race__name='Cult', cult_rank=4).count()
    output['leader_cults'] = EnemyTemplate.objects.filter(published=True, race__name='Cult', cult_rank=5).count()
    
    return output
    
def save_as_html(context):
    ''' Renders the generated enemies to html and saves to disk, so that it can be converted to PDF later '''
    rendered = render_to_string('generated_enemies.html', context)
    prefix = _get_html_prefix(context).encode('utf-8')
    file = NamedTemporaryFile(mode='w', prefix=prefix, suffix='.html', dir='/projects/rq_tools/temp/', delete=False)
    file.write(rendered.encode('utf-8'))
    file.close()
    return file.name
    
def _get_html_prefix(context):
    party = context.get('party', None)
    if party:
        prefix = 'rq_%s_' % party.name.replace(' ', '_')
    else:
        try:
            prefix = 'rq_%s_' % context['enemies'][0].name.replace(' ', '_').replace('_1', 's').replace('/', '_')
            prefix = prefix.replace('"', '')
        except:
            prefix = 'rq_'
    return prefix
    
def generate_pdf(html_path):
    ''' Generates a PDF based on the given html file '''
    pdf_path = html_path.replace('.html', '.pdf')
    #os.system('wkhtmltopdf.sh --enable-forms "%s" "%s" > /dev/null' % (html_path.encode('utf-8'), pdf_path.encode('utf-8')))
    os.system('wkhtmltopdf.sh --enable-forms "%s" "%s" > /projects/rq_tools/pdf.log 2>&1' % (html_path.encode('utf-8'), pdf_path.encode('utf-8')))
    return pdf_path
  
def generate_pngs(html_path):
    ''' Generates png-images out of the generated_html '''
    with open(html_path.encode('utf-8'), 'r') as ff:
        soup = BeautifulSoup(ff)
    enemies = soup.find_all('div', {'class': 'enemy_container'})
    container = soup.find('div', {'id': 'enemies'})
    pngs = []
    for enemy in enemies:
        container.clear()
        container.append(enemy)
        htmlfile = NamedTemporaryFile(mode='w', suffix='.html', dir='/projects/rq_tools/temp/', delete=False)
        htmlfile.write(soup.prettify('utf-8', formatter='html'))
        htmlfile.close()
        png_name = htmlfile.name.replace('.html', '.png')
        os.system('wkhtmltoimage.sh --crop-w 430 "%s" "%s" > /projects/rq_tools/png.log 2>&1' % (htmlfile.name, png_name))
        pngs.append(png_name)
    return pngs
