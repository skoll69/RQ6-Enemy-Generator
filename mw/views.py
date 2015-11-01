from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404

from mw import models as m
from mw import views_lib as lib
from enemygen.views_lib import generate_pdf, save_as_html, generate_pngs, get_filter, get_party_filter
import os


def index(request):
    context = lib.get_context(request)
    context['templates'] = lib.get_enemy_templates(get_filter(request), request.user)
    return render(request, 'mw/index.html', context)


def home(request):
    context = lib.get_context(request)
    context['templates'] = lib.get_enemy_templates('Starred', request.user)
    return render(request, 'mw/home.html', context)


def party_index(request):
    party_filter = lib.get_party_filter(request)
    context = lib.get_context(request)
    context['parties'] = lib.get_party_templates(party_filter)
    return render(request, 'mw/party_index.html', context)


def generate_enemies(request):
    if not request.POST:
        return redirect('index')
    context = lib.get_context(request)
    if request.POST.get('lucky', None):
        context['enemies'] = lib.get_enemies_lucky(request)
        context['single_template'] = True
    else:
        enemy_index = lib.determine_enemies(request.POST)
        increment = False if request.POST.get('dont_increment') else True  # Increment the number of enemies generated
        context['enemies'] = lib.get_enemies(enemy_index, increment)
        context['single_template'] = (len(enemy_index) == 1)
    context['generated_html'] = save_as_html(context, 'mw/generated_enemies.html')
    return render(request, 'mw/generated_enemies.html', context)


def generate_party(request):
    if not request.POST:
        return redirect('party_index')
    context = lib.get_context(request)
    if request.POST.get('lucky', None):
        party_filter = get_party_filter(request)
        party_object = lib.get_random_party(party_filter)
    else:
        party_object = m.MWParty.objects.get(id=request.POST['party_id'])
    context.update(lib.get_generated_party(party_object))
    context['generated_html'] = save_as_html(context, 'mw/generated_enemies.html')
    return render(request, 'mw/generated_enemies.html', context)


@login_required
def edit_index(request):
    context = lib.get_context(request)
    templates = m.MWEnemyTemplate.objects.filter(owner=request.user)
    for et in templates:
        et.starred = et.is_starred(request.user)
    context['enemy_templates'] = templates
    context['edit_parties'] = m.MWParty.objects.filter(owner=request.user)
    return render(request, 'mw/edit_index.html', context)


def enemy_template(request, enemy_template_id):
    context = lib.get_context(request)
    template = 'mw/enemy_template.html'
    et = get_object_or_404(m.MWEnemyTemplate, id=enemy_template_id)
    et.starred = et.is_starred(request.user)
    if et.owner != request.user:
        template = 'mw/enemy_template_read_only.html'
    context.update(lib.get_et_context(et))
    return render(request, template, context)


def party(request, party_id):
    template = 'mw/party.html'
    context = lib.get_context(request)
    context.update(lib.get_party_context(m.MWParty.objects.get(id=party_id)))
    if context['party'].owner != request.user:
        template = 'mw/party_read_only.html'
    return render(request, template, context)


def statistics(request):
    context = lib.get_context(request)
    context['statistics'] = lib.get_statistics()
    return render(request, 'mw/statistics.html', context)


def instructions(request):
    context = lib.get_context(request)
    return render(request, 'mw/instructions.html', context)


def about(request):
    context = lib.get_context(request)
    return render(request, 'mw/about.html', context)


def whats_new(request):
    context = lib.get_context(request)
    context['whats_new'] = m.ChangeLog.objects.all().reverse()
    return render(request, 'mw/whats_new.html', context)


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
        pdf_path = generate_pdf(request.GET.get('generated_html'))
        file_name, extension = os.path.splitext(os.path.basename(pdf_path))
        file_name = '_'.join(file_name.split('_')[:-1])  # Remove the last unique identifier from file name
        file_name = file_name.replace(',', '')
        file_name += extension
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
    et = m.MWEnemyTemplate.create(owner=request.user)
    return redirect(enemy_template, et.id)


@login_required
def create_party(request):
    p = m.MWParty.create(request.user)
    return redirect(party, p.id)


@login_required
def delete_template(request, template_id):
    context = lib.get_context(request)
    et = get_object_or_404(m.MWEnemyTemplate, id=template_id, owner=request.user)
    context['et'] = et
    if request.POST:
        answer = request.POST.get('answer')
        if answer == 'Yes':
            et.delete()
            return redirect(edit_index)
        elif answer == 'No':
            return redirect(enemy_template, template_id)
    return render(request, 'mw/delete_template.html', context)


@login_required
def clone_template(request, template_id):
    et = m.MWEnemyTemplate.objects.get(id=template_id)
    new = et.clone(request.user)
    return redirect(enemy_template, new.id)


@login_required
def clone_party(request, party_id):
    p = m.MWParty.objects.get(id=party_id)
    new = p.clone(request.user)
    return redirect(party, new.id)


@login_required
def apply_skill_bonus(request, template_id):
    et = m.MWEnemyTemplate.objects.get(id=template_id)
    if request.POST:
        et.apply_skill_bonus(request.POST.get('bonus'))
    return redirect(enemy_template, et.id)


@login_required
def delete_party(request, party_id):
    context = lib.get_context(request)
    p = get_object_or_404(m.MWParty, id=party_id, owner=request.user)
    context['party'] = p
    if request.POST:
        answer = request.POST.get('answer')
        if answer == 'Yes':
            p.delete()
            return redirect(edit_index)
        elif answer == 'No':
            return redirect(party, party_id)
    return render(request, 'mw/delete_party.html', context)
