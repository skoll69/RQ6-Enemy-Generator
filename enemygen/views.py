from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template import RequestContext

from enemygen.models import EnemyTemplate, Ruleset, EnemyTemplate, Race, Party, ChangeLog, AdditionalFeatureList
from enemygen.views_lib import get_ruleset, get_context, get_et_context, get_enemies
from enemygen.views_lib import get_enemy_templates, is_race_admin, get_statistics
from enemygen.views_lib import generate_pdf, get_filter, get_party_templates, save_as_html
from enemygen.views_lib import get_party_enemies, spirit_options

def index(request):
    filter = get_filter(request)
    context = get_context(request)
    context['templates'] = get_enemy_templates(filter, request.user)
    return render(request, 'index.html', context)
    
def party_index(request):
    context = get_context(request)
    context['parties'] = get_party_templates()
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

@login_required
def edit_index(request):
    context = get_context(request)
    context['enemy_templates'] = EnemyTemplate.objects.filter(owner=request.user)
    context['races'] = Race.objects.filter(published=True)
    context['edit_races'] = Race.objects.filter(owner=request.user)
    context['edit_parties'] = Party.objects.filter(owner=request.user)
    context['race_admin'] = is_race_admin(request.user)
    return render(request, 'edit_index.html', context)
    
def enemy_template(request, enemy_template_id):
    context = get_context(request)
    template = 'enemy_template.html'
    et = get_object_or_404(EnemyTemplate, id=enemy_template_id)
    if et.owner != request.user:
        template = 'enemy_template_read_only.html'
    context.update(get_et_context(et))
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
    context['all_party_tags'] = sorted(list(Party.tags.all()), key=lambda x: x.name)
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

def about(request):
    context = get_context(request)
    return render(request, 'about.html', context)
    
def whats_new(request):
    context = get_context(request)
    context['whats_new'] = ChangeLog.objects.all().reverse()
    return render(request, 'whats_new.html', context)
    
@login_required
def ruleset(request, ruleset_id):
    context = get_context(request)
    context['ruleset'] = Ruleset.objects.get(id=ruleset_id)
    return render(request, 'ruleset.html', context)
    
def account(request):
    context = get_context(request)
    return render(request, 'account.html', context)
    
def set_filter(request):
    if request.POST:
        filter = request.POST.get('filter', None)
        request.session['filter'] = filter
        return redirect(request.POST['coming_from'])
    return redirect(index)

def feature_items(request, feature_id):
    context = get_context(request)
    context['feature'] = get_object_or_404(AdditionalFeatureList, id=feature_id)
    return render(request, 'feature_items.html', context)
    
    

###############################################################
# Action views
def select_setting_ruleset(request):
    if request.POST:
        #setting_id = int(request.POST.get('setting_id', 1))
        #request.session['setting_id'] = setting_id
        return redirect(request.POST['coming_from'])
    return redirect(index)

def pdf_export(request):
    if request.GET and request.GET.get('action') == 'pdf_export':
        pdf_path = generate_pdf(request.GET.get('generated_html'))
        file_name = pdf_path.split('/')[-1:][0]
        file_name = '_'.join(file_name.split('_')[:-1]) # Remove the last unique identifier from file name
        file_name = file_name.replace(',', '')
        data = open(pdf_path).read()
        response = HttpResponse(data, mimetype='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="%s"' % file_name
        response['Content-Length'] = len(data)
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
    ruleset = get_ruleset(request)
    race_id = int(request.POST.get('race_id'))
    if race_id == 0:
        return redirect(edit_index)
    race = Race.objects.get(id=race_id)
    et = EnemyTemplate.create(owner=request.user, ruleset=ruleset, race=race)
    return redirect(enemy_template, et.id)

@login_required
def create_race(request):
    rc = Race.create(owner=request.user)
    return redirect(race, rc.id)

@login_required
def create_party(request):
    p = Party.create(request.user)
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
        
