from enemygen.models import Setting, Ruleset, EnemyTemplate, Race, Weapon
from enemygen.models import SpellAbstract, EnemySpell, CustomSpell
from enemygen.models import Weapon, CombatStyle, EnemyWeapon, CustomWeapon

def get_setting(request):
    return Setting.objects.get(id=request.session.get('setting_id', 1))
    
def get_ruleset(request):
    return Ruleset.objects.get(id=request.session.get('ruleset_id', 1))

def get_context(request):
    context = {}
    context['setting'] = get_setting(request).name
    context['settings'] = Setting.objects.all().order_by('name')
    context['ruleset'] = get_ruleset(request).name
    context['races'] = Race.objects.all()
    context['generated'] = _get_generated_amount()
    return context

def get_enemy_templates(ruleset, setting, user):
    templates = list(EnemyTemplate.objects.filter(ruleset=ruleset, setting=setting, published=True).order_by('rank'))
    # Add the unpublished templates of the logged-in user
    if user.is_authenticated():
        templates.extend(list(EnemyTemplate.objects.filter(ruleset=ruleset, setting=setting, published=False, owner=user)))
    if user.is_authenticated() and is_superuser(user):
        templates.extend(list(EnemyTemplate.objects.filter(ruleset=ruleset, setting=setting, published=False).exclude(owner=user)))
    return templates
    
def get_enemies(request):
    enemies = []
    index = []
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
    
