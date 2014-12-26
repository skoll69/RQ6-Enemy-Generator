from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template import RequestContext

from enemygen.models import EnemyTemplate, EnemyTemplate, Race, Party, ChangeLog, AdditionalFeatureList
from enemygen.views_lib import get_ruleset, get_context, get_et_context, get_enemies, get_generated_party
from enemygen.views_lib import get_enemy_templates, is_race_admin, get_statistics, get_random_party
from enemygen.views_lib import generate_pdf, get_filter, get_party_templates, save_as_html, generate_pngs
from enemygen.views_lib import spirit_options, get_party_context, get_enemies_lucky, get_party_filter

def index(request):
    filter = get_filter(request)
    context = get_context(request)
    context['templates'] = get_enemy_templates(filter, request.user)
    return render(request, 'index.html', context)
    
def home(request):
    filter = get_filter(request)
    context = get_context(request)
    context['templates'] = get_enemy_templates('Starred', request.user)
    return render(request, 'home.html', context)
    
def party_index(request):
    filter = get_party_filter(request)
    context = get_context(request)
    context['parties'] = get_party_templates(filter)
    return render(request, 'party_index.html', context)
    
def generate_enemies(request):
    if not request.POST:
        return redirect('index')
    context = get_context(request)
    if request.POST.get('lucky', None):
        context['enemies'] = get_enemies_lucky(request)
    else:
        context['enemies'] = get_enemies(request)
    context['generated_html'] = save_as_html(context)
    return render(request, 'generated_enemies.html', context)
    
def generate_party(request):
    if not request.POST:
        return redirect('party_index')
    context = get_context(request)
    if request.POST.get('lucky', None):
        filter = get_party_filter(request)
        party = get_random_party(filter)
    else:
        party = Party.objects.get(id=request.POST['party_id'])
    context.update(get_generated_party(party))
    context['generated_html'] = save_as_html(context)
    return render(request, 'generated_enemies.html', context)

@login_required
def edit_index(request):
    context = get_context(request)
    templates = EnemyTemplate.objects.filter(owner=request.user).exclude(race__name='Cult')
    for et in templates:
        et.starred = et.is_starred(request.user)
    context['enemy_templates'] = templates
    context['races'] = Race.objects.filter(published=True).exclude(name='Cult')
    context['edit_races'] = Race.objects.filter(owner=request.user)
    context['edit_cults'] = EnemyTemplate.objects.filter(owner=request.user, race__name='Cult')
    context['edit_parties'] = Party.objects.filter(owner=request.user)
    context['race_admin'] = is_race_admin(request.user)
    return render(request, 'edit_index.html', context)
    
def enemy_template(request, enemy_template_id):
    context = get_context(request)
    template = 'enemy_template.html'
    et = get_object_or_404(EnemyTemplate, id=enemy_template_id)
    et.starred = et.is_starred(request.user)
    if et.is_cult:
        template = 'enemy_template_cult.html'
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
    party = Party.objects.get(id=party_id)
    context.update(get_party_context(party))
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
    
def account(request):
    context = get_context(request)
    return render(request, 'account.html', context)
    
def feature_items(request, feature_id):
    context = get_context(request)
    context['feature'] = get_object_or_404(AdditionalFeatureList, id=feature_id)
    return render(request, 'feature_items.html', context)
    
    

###############################################################
# Action views
def set_filter(request):
    if request.POST:
        filter = request.POST.get('filter', None)
        request.session['filter'] = filter
        return redirect(request.POST['coming_from'])
    return redirect(index)

def set_party_filter(request):
    if request.POST:
        filter = request.POST.get('party_filter', None)
        request.session['party_filter'] = filter
        return redirect(request.POST['coming_from'])
    return redirect(index)

def pdf_export(request):
    if request.GET and request.GET.get('action') == 'pdf_export':
        pdf_path = generate_pdf(request.GET.get('generated_html'))
        file_name = pdf_path.split('/')[-1:][0]
        file_name = '_'.join(file_name.split('_')[:-1]) # Remove the last unique identifier from file name
        file_name = file_name.replace(',', '')
        data = open(pdf_path.encode('utf-8')).read()
        response = HttpResponse(data, mimetype='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="%s"' % file_name.encode('utf-8')
        response['Content-Length'] = len(data)
        return response

def png_export(request):
    if request.GET and request.GET.get('action') == 'png_export':
        png_paths = generate_pngs(request.GET.get('generated_html'))
        new_paths = []
        for path in png_paths:
            new_paths.append(path.replace('/projects/rq_tools/temp/', '/rq_temp/'))
        return render(request, 'generated_enemies_as_pngs.html', {'png_paths': new_paths})
        
@login_required
def create_enemy_template(request):
    race_id = request.POST.get('race_id')
    if race_id is None:
        return redirect(edit_index)
    race = Race.objects.get(id=race_id)
    et = EnemyTemplate.create(owner=request.user, ruleset=get_ruleset(request), race=race)
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
def create_cult(request):
    race = Race.objects.get(name='Cult')
    et = EnemyTemplate.create(owner=request.user, ruleset=get_ruleset(request), race=race)
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
def clone_party(request, party_id):
    p = Party.objects.get(id=party_id)
    new = p.clone(request.user)
    return redirect(party, new.id)
    
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
        
