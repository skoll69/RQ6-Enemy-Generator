from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template import RequestContext

from enemygen.models import EnemyTemplate, Setting, Ruleset, EnemyTemplate, Race, Weapon, Party
from enemygen.views_lib import get_setting, get_ruleset, get_context, get_enemies, spell_list
from enemygen.views_lib import get_enemy_templates, combat_styles, is_race_admin, get_statistics
from enemygen.views_lib import generate_pdf, get_setting_id, get_party_templates, save_as_html
from enemygen.views_lib import get_party_enemies

def index(request):
    setting_id = get_setting_id(request)
    context = get_context(request)
    context['templates'] = get_enemy_templates(setting_id, request.user)
    return render(request, 'index.html', context)
    
def party_index(request):
    setting_id = get_setting_id(request)
    context = get_context(request)
    context['parties'] = get_party_templates(setting_id)
    return render(request, 'party_index.html', context)
    
def generate_enemies(request):
    if not request.POST:
        return redirect('index')
    context = get_context(request)
    context['enemies'] = get_enemies(request)
    context['generated_html'] = save_as_html(context)
    return render(request, 'generated_enemies.html', context)

def generate_party(request):
    if not request.POST:
        return redirect('party_index')
    context = get_context(request)
    party = Party.objects.get(id=int(request.POST['party_id']))
    context['party'] = party
    context['enemies'] = get_party_enemies(party)
    context['generated_html'] = save_as_html(context)
    return render(request, 'generated_enemies.html', context)

def select_setting_ruleset(request):
    if request.POST:
        setting_id = int(request.POST.get('setting_id', 1))
        request.session['setting_id'] = setting_id
        return redirect(request.POST['coming_from'])
    return redirect(index)

@login_required
def edit_index(request):
    context = get_context(request)
    context['enemy_templates'] = EnemyTemplate.objects.filter(owner=request.user)
    context['edit_races'] = Race.objects.filter(owner=request.user)
    context['edit_parties'] = Party.objects.filter(owner=request.user)
    context['race_admin'] = is_race_admin(request.user)
    return render(request, 'edit_index.html', context)
    
def enemy_template(request, enemy_template_id):
    context = get_context(request)
    template = 'enemy_template.html'
    context['et'] = EnemyTemplate.objects.get(id=enemy_template_id)
    if context['et'].owner != request.user and request.user.username != 'admin':
        template = 'enemy_template_read_only.html'
    context['weapons'] = {}
    context['weapons']['1h'] = Weapon.objects.filter(type='1h-melee')
    context['weapons']['2h'] = Weapon.objects.filter(type='2h-melee')
    context['weapons']['ranged'] = Weapon.objects.filter(type='ranged')
    context['weapons']['shields'] = Weapon.objects.filter(type='shield')
    context['theism_spells'] = spell_list('theism', enemy_template_id)
    context['folk_spells'] = spell_list('folk', enemy_template_id)
    context['sorcery_spells'] = spell_list('sorcery', enemy_template_id)
    context['combat_styles'] = combat_styles(enemy_template_id)
    return render(request, template, context)
    
def race(request, race_id):
    template = 'race.html'
    context = get_context(request)
    context['race'] = Race.objects.get(id=race_id)
    if context['race'].owner != request.user:
        template = 'race_read_only.html'
    return render(request, template, context)

def party(request, party_id):
    template = 'party.html'
    context = get_context(request)
    context['party'] = Party.objects.get(id=party_id)
    context['templates'] = EnemyTemplate.objects.filter(published=True).order_by('name')
    if context['party'].owner != request.user:
        template = 'party_read_only.html'
    return render(request, template, context)

def statistics(request):
    context = get_context(request)
    context['statistics'] = get_statistics()
    return render(request, 'statistics.html', context)

def instructions(request):
    context = get_context(request)
    return render(request, 'instructions.html', context)

def disclaimer(request):
    context = get_context(request)
    return render(request, 'disclaimer.html', context)

    
@login_required
def ruleset(request, ruleset_id):
    context = get_context(request)
    context['ruleset'] = Ruleset.objects.get(id=ruleset_id)
    return render(request, 'ruleset.html', context)

###############################################################
# Action views
def pdf_export(request):
    if request.GET and request.GET.get('action') == 'pdf_export':
        pdf_path = generate_pdf(request.GET.get('generated_html'))
        file_name = pdf_path.split('/')[-1:][0]
        file_name = '_'.join(file_name.split('_')[:-1]) # Remove the last unique identifier from file name
        fsock = open(pdf_path)
        response = HttpResponse(fsock, mimetype=('application/pdf', None))
        response['Content-Disposition'] = 'attachment; filename=%s' % file_name
        return response

@login_required
def add_template_to_party(request):
    if request.POST:
        p = Party.objects.get(id=int(request.POST['party_id']))
        t = EnemyTemplate.objects.get(id=int(request.POST['template_id']))
        p.add(t)
        return redirect(party, p.id)
    
@login_required
def create_enemy_template(request):
    setting = get_setting(request)
    ruleset = get_ruleset(request)
    race_id = int(request.POST.get('race_id'))
    if race_id == 0:
        return redirect(edit_index)
    race = Race.objects.get(id=race_id)
    et = EnemyTemplate.create(owner=request.user, setting=setting, ruleset=ruleset, race=race)
    return redirect(enemy_template, et.id)

@login_required
def create_race(request):
    rc = Race.create(owner=request.user)
    return redirect(race, rc.id)

@login_required
def create_party(request):
    setting = get_setting(request)
    p = Party.create(request.user, setting)
    return redirect(party, p.id)

@login_required
def delete_template(request, template_id):
    context = get_context(request)
    try:
        et = EnemyTemplate.objects.get(id=template_id, owner=request.user)
    except EnemyTemplate.DoesNotExist:
        et = None
    context['et'] = et
    if request.POST:
        answer = request.POST.get('answer')
        if answer == 'Yes':
            et.delete()
            return redirect(edit_index)
        elif answer == 'No':
            return redirect(enemy_template, template_id)
    return render(request, 'delete_template.html', context)
    
@login_required
def clone_template(request, template_id):
    et = EnemyTemplate.objects.get(id=template_id)
    new = et.clone(request.user)
    return redirect(enemy_template, new.id)
    
@login_required
def clone_race(request, race_id):
    new = Race.objects.get(id=race_id).clone(request.user)
    return redirect(race, new.id)
    
@login_required
def apply_skill_bonus(request, template_id):
    et = EnemyTemplate.objects.get(id=template_id)
    if request.POST:
        et.apply_skill_bonus(request.POST.get('bonus'))
    return redirect(enemy_template, et.id)
    
@login_required
def delete_race(request, race_id):
    context = get_context(request)
    try:
        rc = Race.objects.get(id=race_id, owner=request.user)
    except Race.DoesNotExist:
        rc = None
    context['race'] = rc
    if request.POST:
        answer = request.POST.get('answer')
        if answer == 'Yes':
            rc.delete()
            return redirect(edit_index)
        elif answer == 'No':
            return redirect(race, race_id)
    return render(request, 'delete_race.html', context)
        
@login_required
def delete_party(request, party_id):
    context = get_context(request)
    try:
        p = Party.objects.get(id=party_id, owner=request.user)
    except Party.DoesNotExist:
        p = None
    context['party'] = p
    if request.POST:
        answer = request.POST.get('answer')
        if answer == 'Yes':
            p.delete()
            return redirect(edit_index)
        elif answer == 'No':
            return redirect(party, party_id)
    return render(request, 'delete_party.html', context)
        
