from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.conf import settings
from django.utils.datastructures import MultiValueDictKeyError

from enemygen.models import EnemyTemplate, Race, Party, ChangeLog, AdditionalFeatureList
from enemygen.views_lib import get_ruleset, get_context, get_et_context, get_enemies, get_generated_party
from enemygen.views_lib import get_enemy_templates, is_race_admin, get_statistics, get_random_party
from enemygen.views_lib import get_filter, get_party_templates, save_as_html
from enemygen.views_lib import get_party_context, get_enemies_lucky, get_party_filter, determine_enemies, as_json, enemy_as_json
from enemygen import views_lib as lib

import os
import json


def index(request):
    context = get_context(request)

    context['templates'] = get_enemy_templates(get_filter(request), request.user)
    return render(request, 'index.html', context)


def simple_index(request):
    context = get_context(request)
    if request.user.is_authenticated:
        templates = EnemyTemplate.objects.filter(owner=request.user)
        paginator = Paginator(templates, 200)
        page = request.GET.get('page')
        try:
            context['templates'] = paginator.page(page)
        except PageNotAnInteger:
            context['templates'] = paginator.page(1)
        except EmptyPage:
            context['templates'] = paginator.page(paginator.num_pages)
    return render(request, 'simple_index.html', context)


def index_json(request):
    out = []
    for et in get_enemy_templates(get_filter(request), request.user):
        out.append({
            'name': et.name, 'race': et.race.name, 'rank': et.rank, 'owner': et.owner.username,
            'tags': et.get_tags(), 'id': et.id, 'notes': et.notes
        })
    return HttpResponse(json.dumps(out), content_type="application/json")

def home(request):
    context = get_context(request)
    context['templates'] = get_enemy_templates('Starred', request.user)
    return render(request, 'home.html', context)


def party_index(request):
    party_filter = get_party_filter(request)
    context = get_context(request)
    context['parties'] = get_party_templates(party_filter)
    return render(request, 'party_index.html', context)


def party_index_json(request):
    out = []
    for party in get_party_templates(get_party_filter(request)):
        party_json = {
            'name': party.name, 'owner': party.owner.username, 'tags': party.get_tags(), 'id': party.id, 'templates': []
        }
        for template in party.template_specs:
            party_json['templates'].append({
                'name': template.template.name,
                'amount': template.amount,
                'id': template.template.id,
            })
        out.append(party_json)

    return HttpResponse(json.dumps(out), content_type="application/json")


def generate_enemies(request):
    if not request.POST:
        return redirect('index')
    context = get_context(request)
    if request.POST.get('lucky', None):
        context['enemies'] = get_enemies_lucky(request)
        context['single_template'] = True
    else:
        enemy_index = determine_enemies(request.POST)
        increment = False if request.POST.get('dont_increment') else True  # Increment the number of enemies generated
        context['enemies'] = get_enemies(enemy_index, increment)
        context['single_template'] = (len(enemy_index) == 1)
    context['generated_html'] = save_as_html(context, 'generated_enemies.html')
    return render(request, 'generated_enemies.html', context)


def generate_enemies_json(request):
    template_id = request.GET.get('id', None)
    if not template_id:
        return redirect('home')
    amount = request.GET.get('amount', 1)
    try:
        template_id = int(template_id)
    except ValueError:
        raise Http404
    try:
        amount = int(amount)
    except ValueError:
        amount = 1
    et = get_object_or_404(EnemyTemplate, id=template_id)
    enemy_index = ((et, int(amount)),)
    enemies = get_enemies(enemy_index, True)
    enemies_json = as_json(enemies)
    return HttpResponse(enemies_json, content_type="application/json")


def generate_party_json(request):
    try:
        party_object = Party.objects.get(id=request.GET['id'])
    except (Party.DoesNotExist, MultiValueDictKeyError):
        raise Http404
    party = get_generated_party(party_object)
    out = {'enemies': [], 'party_name': party['party'].name, 'additional_features': []}
    for enemy in party['enemies']:
        out['enemies'].append(enemy_as_json(enemy))
    for af in party['party_additional_features']:
        out['additional_features'].append({'name': af.name, 'feature': af.feature_list.name})
    out = json.dumps(out)
    return HttpResponse(out, content_type="application/json")


def generate_party(request):
    if not request.POST:
        return redirect('party_index')
    context = get_context(request)
    if request.POST.get('lucky', None):
        party_filter = get_party_filter(request)
        party_object = get_random_party(party_filter)
    else:
        party_object = Party.objects.get(id=request.POST['party_id'])
    context.update(get_generated_party(party_object))
    context['generated_html'] = save_as_html(context, 'generated_enemies.html')
    return render(request, 'generated_enemies.html', context)


@login_required
def edit_index(request):
    context = get_context(request)
    templates = EnemyTemplate.objects.filter(owner=request.user).exclude(race__name='Cult').select_related('race')
    for et in templates:
        et.starred = et.is_starred(request.user)
    context['enemy_templates'] = templates
    context['races'] = Race.objects.filter(published=True).exclude(name='Cult')
    context['edit_cults'] = EnemyTemplate.objects.filter(owner=request.user, race__name='Cult')
    context['edit_parties'] = Party.objects.filter(owner=request.user)
    context['race_admin'] = is_race_admin(request.user)
    return render(request, 'edit_index.html', context)


@login_required
def race_index(request):
    context = get_context(request)
    if not is_race_admin(request.user):
        raise Http404
    context['edit_races'] = Race.objects.filter(owner=request.user)
    return render(request, 'race_index.html', context)


def enemy_template(request, enemy_template_id):
    context = get_context(request)
    template = 'enemy_template.html'
    et = get_object_or_404(EnemyTemplate.objects.select_related('race'), id=enemy_template_id)
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
    pt = get_object_or_404(Party, id=party_id)
    context.update(get_party_context(pt))
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
        request.session['filter'] = request.POST.get('filter', None)
        return redirect(request.POST['coming_from'])
    return redirect(index)


def set_party_filter(request):
    if request.POST:
        request.session['party_filter'] = request.POST.get('party_filter', None)
        return redirect(request.POST['coming_from'])
    return redirect(index)


def pdf_export(request):
    if request.GET and request.GET.get('action') == 'pdf_export':
        pdf_path = lib.generate_pdf(request.GET.get('generated_html'))
        file_name, extension = os.path.splitext(os.path.basename(pdf_path))
        file_name = '_'.join(file_name.split('_')[:-1])  # Remove the last unique identifier from file name
        file_name = file_name.replace(',', '')
        file_name += extension
        data = open(pdf_path, 'rb').read()
        response = HttpResponse(data, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="%s"' % file_name
        response['Content-Length'] = len(data)
        return response
    return redirect('home')


def png_export(request):
    if request.GET and request.GET.get('action') == 'png_export':
        png_paths = lib.generate_pngs(request.GET.get('generated_html'))
        new_paths = []
        for path in png_paths:
            fileName = os.path.basename(path)
            new_paths.append('/temp/' + fileName)
        return render(request, 'generated_enemies_as_pngs.html', {'png_paths': new_paths})
    return redirect('home')


@login_required
def create_enemy_template(request):
    race_id = request.POST.get('race_id')
    if race_id is None:
        return redirect(edit_index)
    race_object = Race.objects.get(id=race_id)
    et = EnemyTemplate.create(owner=request.user, ruleset=get_ruleset(request), race=race_object)
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
    cult_race = Race.objects.get(name='Cult')
    et = EnemyTemplate.create(owner=request.user, ruleset=get_ruleset(request), race=cult_race)
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
