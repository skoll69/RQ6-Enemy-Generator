from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template import RequestContext

from enemygen.models import EnemyTemplate, Setting, Ruleset, EnemyTemplate, Race, Weapon
from enemygen.views_lib import get_setting, get_ruleset, get_context, get_enemies, spell_list
from enemygen.views_lib import get_enemy_templates, combat_styles, is_race_admin

def index(request):
    setting = get_setting(request)
    ruleset = get_ruleset(request)
    context = get_context(request)
    context['templates'] = get_enemy_templates(ruleset, setting, request.user)
    return render(request, 'index.html', context)
    
def generate_enemies(request):
    if not request.POST:
        return redirect('index')
    context = get_context(request)
    context['enemies'] = get_enemies(request)
    return render(request, 'generated_enemies.html', context)

def select_setting_ruleset(request):
    if request.POST:
        setting_id = int(request.POST.get('setting_id', 1))
        request.session['setting_id'] = setting_id
    return redirect(index)

@login_required
def edit_index(request):
    context = get_context(request)
    context['enemy_templates'] = EnemyTemplate.objects.filter(owner=request.user)
    context['edit_races'] = Race.objects.filter(owner=request.user)
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

@login_required
def create_race(request):
    rc = Race.create(owner=request.user)
    return redirect(race, rc.id)

    
@login_required
def ruleset(request, ruleset_id):
    context = get_context(request)
    context['ruleset'] = Ruleset.objects.get(id=ruleset_id)
    return render(request, 'ruleset.html', context)

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
        
def instructions(request):
    context = get_context(request)
    return render(request, 'instructions.html', context)
