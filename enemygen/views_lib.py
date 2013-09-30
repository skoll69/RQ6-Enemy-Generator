from enemygen.models import Setting, Ruleset, EnemyTemplate, Race, Weapon
from enemygen.models import SpellAbstract, EnemySpell, CustomSpell
from enemygen.models import Weapon, CombatStyle, EnemyWeapon, CustomWeapon, Party

from django.contrib.auth.models import User
from django.template.loader import render_to_string

from tempfile import NamedTemporaryFile
import os

def get_setting_id(request):
    return int(request.session.get('setting_id', 0))

def get_setting(request):
    setting_id = int(request.session.get('setting_id', 0))
    if setting_id:
        settings = Setting.objects.get(id=setting_id)
    else:
        settings = Setting.objects.all()[0]
    return settings
    
def get_ruleset(request):
    return Ruleset.objects.get(id=request.session.get('ruleset_id', 1))

def get_context(request):
    context = {}
    context['setting_id'] = get_setting_id(request)
    context['settings'] = Setting.objects.all().order_by('name')
    context['races'] = Race.objects.all()
    context['generated'] = _get_generated_amount()
    context['request'] = request
    return context

def get_party_templates(setting_id):
    settings = _get_settings(setting_id)
    parties = list(Party.objects.filter(setting__in=settings, published=True))
    return parties
    
def get_enemy_templates(setting_id, user):
    settings = _get_settings(setting_id)
    templates = list(EnemyTemplate.objects.filter(setting__in=settings, published=True).order_by('rank'))
    # Add the unpublished templates of the logged-in user
    if user.is_authenticated():
        templates.extend(list(EnemyTemplate.objects.filter(setting__in=settings, published=False, owner=user)))
    if user.is_authenticated() and is_superuser(user):
        templates.extend(list(EnemyTemplate.objects.filter(setting__in=settings, published=False).exclude(owner=user)))
    return templates
    
def _get_settings(setting_id):
    if setting_id == 0:
        settings = Setting.objects.all()
    else:
        settings = Setting.objects.filter(id=setting_id)
    return settings
    
def get_enemies(request):
    enemies = []
    index = []
    increment = False if request.POST.get('dont_increment') else True   # Increment the number of enemies generated?
    for key, amount in request.POST.items():
        if not 'enemy_template_id_' in key: continue
        enemy_template_id = int(key.replace('enemy_template_id_', ''))
        et = EnemyTemplate.objects.get(id=enemy_template_id)
        try:
            amount = int(amount)
        except ValueError:
            amount = 0
        if amount > 40: amount = 40
        index.append((et, amount))
    index.sort(key=lambda tup: tup[0].rank, reverse=True)
    for et, amount in index:
        if increment:
            et.increment_used()
        for i in xrange(amount):
            enemies.append(et.generate(i+1, increment))
    return enemies
    
def get_party_enemies(party):
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
    
def spell_list(type, et_id):
    ''' Returns the list of the given type of spells for the given EnemyTemplate '''
    output = []
    for spell in SpellAbstract.objects.filter(type=type):
        try:
            es = EnemySpell.objects.get(spell=spell, enemy_template__id=et_id)
            prob = es.probability
            detail_text = es.detail
        except EnemySpell.DoesNotExist:
            prob = 0
            detail_text = spell.default_detail
        sp = {'id': spell.id, 'name': spell.name, 'probability': prob, 'detail_text': detail_text}
        sp['detail'] = spell.detail
        output.append(sp)
    for spell in CustomSpell.objects.filter(enemy_template__id=et_id, type=type):
        sp = {'id': spell.id, 'name': spell.name, 'probability': spell.probability, 'custom': True}
        output.append(sp)
    return output
    
def combat_styles(et_id):
    ''' Returns a list of combat styles, that contains a list of weapons. The weaponlist contains
        all weapons in the system. The weapons, that have been selected to the CombatStyle (by
        assigning a probability) have also their probability listed.
    '''
    output = []
    for cs in CombatStyle.objects.filter(enemy_template__id=et_id):
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
    
def is_race_admin(user):
    return bool(user.groups.filter(name='race_admin').count())
    
def is_superuser(user):
    return bool(user.groups.filter(name='superuser').count())
    
def get_statistics():
    output = {}
    
    templates = list((et.name, et.generated, et.id) for et in EnemyTemplate.objects.filter(published=True))
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
    
    return output
    
def save_as_html(context):
    ''' Renders the generated enemies to html and saves to disk, so that it can be converted to PDF later '''
    rendered = render_to_string('generated_enemies.html', context)
    prefix = _get_html_prefix(context)
    file = NamedTemporaryFile(mode='w', prefix=prefix, suffix='.html', dir='/projects/rq_tools/temp/', delete=False)
    file.write(rendered)
    file.close()
    return file.name
    
def _get_html_prefix(context):
    party = context.get('party', None)
    if party:
        prefix = 'rq_%s_' % party.name.replace(' ', '_')
    else:
        try:
            prefix = 'rq_%s_' % context['enemies'][0].name.replace(' ', '_').replace('_1', 's')
        except:
            prefix = 'rq_'
    return prefix
    
def generate_pdf(html_path):
    ''' Generates a PDF based on the given html file '''
    pdf_path = html_path.replace('.html', '.pdf')
    #os.system('wkhtmltopdf.sh --enable-forms "%s" "%s" > /dev/null' % (html_path, pdf_path))
    os.system('wkhtmltopdf.sh --enable-forms "%s" "%s" > /projects/rq_tools/pdf.log 2>&1' % (html_path, pdf_path))
    return pdf_path
    
    