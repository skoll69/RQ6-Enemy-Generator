async function submit(id, type, input_object, value, parent_id){
    //Called when a field is changed
    const res = await axios.post(`/rest/submit/${id}/`, {value, 'object': type, parent_id});
    submit_callback(res.data, input_object);
}

async function add_custom_skill(event){
    var et_id = $(event.target).attr('et_id');
    await axios.post(`/rest/add_custom_skill/${et_id}/`);
    refresh_page();
}

async function add_additional_feature(event){
    var parent_id = $(event.target).attr('parent_id');
    var type = $(event.target).attr('object_type');
    var feature_list_id = $('#additional_feature_options').val();
    await axios.post(`/rest/add_additional_feature/${parent_id}/`, {feature_list_id, type});
    refresh_page();
}

async function add_custom_spell(event){
    var type = $(event.target).attr('type');
    var et_id = $(event.target).attr('et_id');
    await axios.post(`/rest/add_custom_spell/${et_id}/${type}/`);
    refresh_page();
}

async function add_spirit(event){
    var spirit_ids = $('#spirit_options').val();
    var et_id = $(event.target).attr('et_id');
    await axios.post(`/rest/add_spirit/${et_id}/`, {spirit_ids});
    refresh_page();
}

async function add_cult(event){
    var cult_ids = $('#cult_options').val();
    var et_id = $(event.target).attr('et_id');
    await axios.post(`/rest/add_cult/${et_id}/`, {cult_ids});
    refresh_page();
}

async function add_template_to_party(event){
    var template_ids = $('#template_ids').val();
    var party_id = $(event.target).attr('party_id');
    await axios.post(`/rest/add_template_to_party/${party_id}/`,  {template_ids});
    refresh_page();
}

async function add_custom_weapon(event){
    var type = $(event.target).attr('type');
    var cs_id = $(event.target).attr('cs_id');
    await axios.post(`/rest/add_custom_weapon/${cs_id}/${type}/`);
    refresh_page();
}

async function add_hit_location(event){
    var race_id = $(event.target).attr('race_id');
    await axios.post(`/rest/add_hit_location/${race_id}/`);
    refresh_page();
}

function get_feature_list_items_callback(result){
    var options = ""
    for (var i=0; i<result.data.length; i++){
        options += '<option title="'+result.data[i].name+'" value="'+ result.data[i].id +'">'+ result.data[i].name +'</option>'
    }
    $('#nonrandom_feature_options').html(options);
}

async function get_feature_list_items(event){
    var list_id = $(event.target).val();
    const res = await axios.get(`/rest/get_feature_list_items/${list_id}/`);
    get_feature_list_items_callback(res.data);
}

async function add_nonrandom_feature(event){
    var et_id = $(event.target).attr('et_id');
    var party_id = $(event.target).attr('party_id');
    var feature_id = $('#nonrandom_feature_options').val()
    let data;
    if (et_id) {
        data = {et_id};
    } else if (party_id) {
        data = {party_id};
    }
    await axios.post(`/rest/add_nonrandom_feature/${feature_id}/`, data);
    refresh_page();
}

async function del_item(event){
    var item_id = $(event.target).attr('item_id');
    var item_type = $(event.target).attr('item_type');
    await axios.post(`/rest/del_item/${item_id}/${item_type}/`);
    refresh_page();
}

async function deltag_submit(id, type, input_object, value){
    const res = await axios.post(`/rest/submit/${id}/`, {'value': value, 'object': type, 'parent_id': null});
    if (res.data.success){
        $(input_object).parent().hide();
    }
}

function deltag(event){
    var et_id = $(event.target).attr('et_id');
    var tag = $(event.target).attr('value');
    deltag_submit(et_id, 'et_deltag', event.target, tag)
}

function del_party_tag(event){
    var party_id = $(event.target).attr('party_id');
    var tag = $(event.target).attr('value');
    deltag_submit(party_id, 'party_deltag', event.target, tag)
}

async function apply_notes_to_templates(event){
    var race_id = $(event.target).attr('item_id');
    var notes = $('#race_notes').html();
    const res = await axios.post(`/rest/apply_notes_to_templates/${race_id}/`, {notes});

    if (res.data.success){
        $('#apply_notes_to_templates_confirmation').show();
        setTimeout(function(){$('#apply_notes_to_templates_confirmation').fadeOut(1000);}, 3000);
    } else {
        console.log(res.data);
    }
}

async function toggle_star(event){
    var et_id = $(event.target).attr('et_id');
    const result = await axios.post(`/rest/toggle_star/${et_id}/`);
    toggle_star_callback(result.data, event.target)
}

function search_callback(result){
    $('div#results_number').html(result.results.length+' templates found.');
    $('#search_results_table tbody').html('');
    var table = $('#enemy_template_list');
    $('div#searching').hide()
    for (i in result.results){
        var row = result.results[i];
        if (row.starred) var star = '<td><img et_id="'+row.id+'" class="star" height="22" width="22" src="/static/images/star_filled.png" /></td>';
        else             var star = '<td><img et_id="'+row.id+'" class="star" height="22" width="22" src="/static/images/star_empty.png" /></td>';
        var name = '<td><a class="edit_item" href="/enemy_template/'+row.id+'/">'+row.name+'</a></td>';
        var input = '<td><input id="enemy_template_id_'+row.id+'" name="enemy_template_id_'+row.id+'" size="4" min="0" max="40" type="number" class="enemy_amount"></td>';
        var race = '<td>'+row.race+'</td>';
        switch(row.rank){
            case 1: var rank = '<td>1&nbsp;Rabble</td>'; break;
            case 2: var rank = '<td>2&nbsp;Novice</td>'; break;
            case 3: var rank = '<td>3&nbsp;Skilled</td>'; break;
            case 4: var rank = '<td>4&nbsp;Veteran</td>'; break;
            case 5: var rank = '<td>5&nbsp;Master</td>'; break;
        }
        var creator = '<td>'+row.owner+'</td>';
        var tags = '<td>';
        for (i in row.tags){
            tags += '<div class="small_tag">'+row.tags[i]+'</div>';
        }
        tags += '</td>';
        var out = '<tr>'+star+name+input+race+rank+creator+tags+'</tr>';
        table.append(out);
    }
    initialize_enemy_list();
    $('input#search').select();
}

async function search(){
    var string = $('input#search').val();
    var rank_filter = [];
    $('input.rank:checked').each(function(){
        rank_filter.push(parseInt($(this).attr('id')));
    })
    var cult_rank_filter = [];
    $('input.cult_rank:checked').each(function(){
        cult_rank_filter.push(parseInt($(this).attr('id')));
    })
    $('#enemy_template_list tr:gt(0)').remove();
    $('#getting_started').remove();
    $('#enemy_template_list').show();
    set_template_list_height();
    $('div#searching').show();
    var data = {'string': string, 'rank_filter': rank_filter, 'cult_rank_filter': cult_rank_filter}
    const res = await axios.get('/rest/search/',  {params: data});
    search_callback(res.data);
}

////////////////////////////////////////
// Index/Home page enemy lists
function template_list_height(){
    if ($('#enemy_template_list').offset()){
        var upper_point = $('#enemy_template_list').offset().top;
    } else if ($('#party_list').offset()){
        var upper_point = $('#party_list').offset().top;
    }
    var list_container_height = $(window).height() - upper_point - 22;
    return list_container_height;
}

function set_column_width(){
    // Set the columns in both table to be of the same width
    if ($('table#enemy_template_list tr:first th').eq(1).width() > $('table#selected_enemy_template_list td').eq(1).width()){
        var c0w = $('table#enemy_template_list tr:first th').eq(0).width();
        var c1w = $('table#enemy_template_list tr:first th').eq(1).width();
        var c2w = $('table#enemy_template_list tr:first th').eq(2).width();
        var c3w = $('table#enemy_template_list tr:first th').eq(3).width();
        var c4w = $('table#enemy_template_list tr:first th').eq(4).width();
        var c5w = $('table#enemy_template_list tr:first th').eq(5).width();
        var c6w = $('table#enemy_template_list tr:first th').eq(6).width();
        
        $('table#selected_enemy_template_list td').eq(0).css('width', c0w)
        $('table#selected_enemy_template_list td').eq(1).css('width', c1w)
        $('table#selected_enemy_template_list td').eq(2).css('width', c2w)
        $('table#selected_enemy_template_list td').eq(3).css('width', c3w)
        $('table#selected_enemy_template_list td').eq(4).css('width', c4w)
        $('table#selected_enemy_template_list td').eq(5).css('width', c5w)
        $('table#selected_enemy_template_list td').eq(6).css('width', c6w)
    } else {
        var c0w = $('table#selected_enemy_template_list tr:first th').eq(0).width();
        var c1w = $('table#selected_enemy_template_list tr:first th').eq(1).width();
        var c2w = $('table#selected_enemy_template_list tr:first th').eq(2).width();
        var c3w = $('table#selected_enemy_template_list tr:first th').eq(3).width();
        var c4w = $('table#selected_enemy_template_list tr:first th').eq(4).width();
        var c5w = $('table#selected_enemy_template_list tr:first th').eq(5).width();
        var c6w = $('table#selected_enemy_template_list tr:first th').eq(6).width();
        
        $('table#enemy_template_list th').eq(0).css('width', c0w)
        $('table#enemy_template_list td').eq(0).css('width', c0w)
        $('table#enemy_template_list th').eq(1).css('width', c1w)
        $('table#enemy_template_list td').eq(1).css('width', c1w)
        $('table#enemy_template_list th').eq(2).css('width', c2w)
        $('table#enemy_template_list td').eq(2).css('width', c2w)
        $('table#enemy_template_list th').eq(3).css('width', c3w)
        $('table#enemy_template_list td').eq(3).css('width', c3w)
        $('table#enemy_template_list th').eq(4).css('width', c4w)
        $('table#enemy_template_list td').eq(4).css('width', c4w)
        $('table#enemy_template_list th').eq(5).css('width', c5w)
        $('table#enemy_template_list td').eq(5).css('width', c5w)
        $('table#enemy_template_list th').eq(6).css('width', c6w)
        $('table#enemy_template_list td').eq(6).css('width', c6w)
    }
}

function set_template_list_height(){
    $('#enemy_template_list_container').css('height', template_list_height());
}

function get_cookie(name){
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].toString().replace(/^\s+/, "").replace(/\s+$/, "");
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
};

$(document).ready(function(){
    window.axios.defaults.headers.common['X-CSRFToken'] = get_cookie('csrftoken');

	$('.data:input[type=number], .data:input[type=text], select.data, textarea.data').blur(function(event){
		bind_change_listeners(event);
	});

	$('input.data:checkbox').change(function(event){
		bind_change_listeners(event);
	});

    $('.data:input[type=number]').change(function(event){
		bind_change_listeners(event);
    });
    
	$('input.data').focus(function(event){
		$(event.target).data("default_value", $(event.target).val());
	});
    
    $('.add_custom_spell').click(function(event){
        add_custom_spell(event);
    })

    $('#add_spirit').click(function(event){
        add_spirit(event);
    })

    $('#add_cult').click(function(event){
        add_cult(event);
    })

    $('#add_template_to_party').click(function(event){
        add_template_to_party(event);
    })

    $('.add_additional_feature').click(function(event){
        add_additional_feature(event);
    })

    $('.add_custom_skill').click(function(event){
        add_custom_skill(event);
    })

    $('.add_custom_weapon').click(function(event){
        add_custom_weapon(event);
    })
    
    $('#add_hit_location').click(function(event){
        add_hit_location(event);
    })
    
    $('.del_item').click(function(event){
        del_item(event);
    })
    
    $('.del_tag').click(function(event){
        deltag(event);
    })
    
    $('.del_party_tag').click(function(event){
        del_party_tag(event);
    })
    
    $('#apply_notes_to_templates').click(function(event){
        apply_notes_to_templates(event);
    })
    
    $('#nonrandom_feature_list_options').change(function(event){
        get_feature_list_items(event);
    });
    
    $('#add_nonrandom_feature').click(function(event){
        add_nonrandom_feature(event);
    });
    
    $('#pro_skill_include_24').change(function(event){  // Shaping
        $('#sorcery_spells_container').toggle();
    })
    $('#pro_skill_include_22').change(function(event){  // Devotion
        $('#theism_spells_container').toggle();
    })
    $('#pro_skill_include_20').change(function(event){  // Folk magician
        $('#folk_spells_container').toggle();
    })
    $('#pro_skill_include_27').change(function(event){  // Animist
        $('#spirits_container').toggle();
    })
    $('#pro_skill_include_30').change(function(event){  // Mystic
        $('#mysticism_spells_container').toggle();
    })
    $('img.star').click(function(event){
        toggle_star(event);
    })
    
    $('button#search_button').click(function(event){
        search();
    });
    $('input#search').keyup(function(e){
        if(e.keyCode == 13) search();   // Enter
    });
    
    if($('#enemy_template_list').length){
        initialize_enemy_list();
    }
    $('input#search').focus();
    
    $('.natural_weapon').change(function(event){
        $(event.target).parent().parent().find('.ap_hp').toggle();
    });
});