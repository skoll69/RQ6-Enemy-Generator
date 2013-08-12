from enemygen.models import Setting, Ruleset, EnemyTemplate, Race, Weapon
from enemygen.models import SpellAbstract, EnemySpell

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

def get_enemy_templates_old(ruleset, setting, user):
    templates = []
    for rank in ((1, 'Rubble'), (2, 'Novice'), (3, 'Skilled'), (4, 'Veteran'), (5, 'Master')):
        templist = list(EnemyTemplate.objects.filter(ruleset=ruleset, setting=setting, 
                                                     published=True, rank=rank[0]))
        # Add the unpublished templates of the logged-in user
        if user.is_authenticated():
            templist.extend(list(EnemyTemplate.objects.filter(ruleset=ruleset, setting=setting,
                                                              published=False, rank=rank[0], owner=user)))
        templates.append({'name': rank[1], 'id': rank[0], 'templates': templist})
    return templates
    
def get_enemy_templates(ruleset, setting, user):
    templates = list(EnemyTemplate.objects.filter(ruleset=ruleset, setting=setting, published=True).order_by('rank'))
    # Add the unpublished templates of the logged-in user
    if user.is_authenticated():
        templates.extend(list(EnemyTemplate.objects.filter(ruleset=ruleset, setting=setting, published=False, owner=user)))
    return templates
    
def get_enemies(request):
    enemies = []
    for key, amount in request.POST.items():
        if not 'enemy_template_id_' in key: continue
        enemy_template_id = int(key.replace('enemy_template_id_', ''))
        et = EnemyTemplate.objects.get(id=enemy_template_id)
        try:
            amount = int(amount)
        except ValueError:
            amount = 0
        if amount > 40: amount = 40
        for i in xrange(amount):
            enemies.append(et.generate(i+1))
    return enemies

def _get_generated_amount():
    n = 0
    for et in EnemyTemplate.objects.all():
        n += et.generated
    return n
    
def spell_list(type, et_id):
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
    return output