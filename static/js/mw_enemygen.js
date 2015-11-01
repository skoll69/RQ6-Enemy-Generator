function submit(id, type, input_object, value, parent_id){
	//Called when a field is changed
    (function(value, id, type, input_object){
        Dajaxice.mw.submit(function(result) {submit_callback(result, input_object)}, {'value': value, 'id': id, 'object': type, 'parent_id': parent_id});
    })(value, id, type, input_object);
}

function add_custom_skill(event){
    var et_id = $(event.target).attr('et_id');
    Dajaxice.mw.add_custom_skill(refresh_page, {'et_id': et_id})
}

function add_additional_feature(event){
    var parent_id = $(event.target).attr('parent_id');
    var type = $(event.target).attr('object_type');
    var feature_list_id = $('#additional_feature_options').val();
    Dajaxice.mw.add_additional_feature(refresh_page, {'parent_id': parent_id, 'feature_list_id': feature_list_id, 'type': type})
}

function add_custom_spell(event){
    var type = $(event.target).attr('type');
    var et_id = $(event.target).attr('et_id');
    Dajaxice.mw.add_custom_spell(refresh_page, {'type': type, 'et_id': et_id})
}

function add_template_to_party(event){
    var template_ids = $('#template_ids').val();
    var party_id = $(event.target).attr('party_id');
    Dajaxice.mw.add_template_to_party(refresh_page, {'template_ids': template_ids, 'party_id': party_id})
}

function add_custom_weapon(event){
    var type = $(event.target).attr('type');
    var cs_id = $(event.target).attr('cs_id');
    Dajaxice.mw.add_custom_weapon(refresh_page, {'type': type, 'cs_id': cs_id})
}

function get_feature_list_items_callback(result){
    var options = ""
    for (var i=0; i<result.data.length; i++){
        options += '<option title="'+result.data[i].name+'" value="'+ result.data[i].id +'">'+ result.data[i].name +'</option>'
    }
    $('#nonrandom_feature_options').html(options);
}

function get_feature_list_items(event){
    var list_id = $(event.target).val();
    Dajaxice.enemygen.get_feature_list_items(get_feature_list_items_callback, {'list_id': list_id})
}

function del_item(event){
    var item_id = $(event.target).attr('item_id');
    var item_type = $(event.target).attr('item_type');
    Dajaxice.mw.del_item(refresh_page, {'item_id': item_id, 'item_type': item_type})
}

function deltag_submit(id, type, input_object, value){
    (function(value, id, type, input_object){
        Dajaxice.mw.submit(function(result) {deltag_callback(result, input_object)}, {'value': value, 'id': id, 'object': type, 'parent_id': null});
    })(value, id, type, input_object);
}

function deltag_callback(result, object){
    if (result.success){
        $(object).parent().hide();
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

function toggle_star(event){
    var et_id = $(event.target).attr('et_id');
    Dajaxice.mw.toggle_star(function(result){toggle_star_callback(result, event.target)}, {'et_id': et_id});
}

function search_callback(result){
    $('div#results_number').html(result.results.length+' templates found.');
    $('#search_results_table tbody').html('');
    var table = $('#enemy_template_list');
    $('div#searching').hide()
    for (i in result.results){
        var row = result.results[i];
        if (row.starred) var star = '<td><img et_id="'+row.id+'" class="star" height="22" width="22" src="/rq_static/images/star_filled.png" /></td>';
        else             var star = '<td><img et_id="'+row.id+'" class="star" height="22" width="22" src="/rq_static/images/star_empty.png" /></td>';
        var name = '<td><a class="edit_item" href="/rq_tools/enemygen/enemy_template/'+row.id+'/">'+row.name+'</a></td>';
        var input = '<td><input id="enemy_template_id_'+row.id+'" name="enemy_template_id_'+row.id+'" size="4" min="0" max="40" type="number" class="enemy_amount"></td>';
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
        var out = '<tr>'+star+name+input+rank+creator+tags+'</tr>';
        table.append(out);
    }
    initialize_enemy_list();
    $('input#search').select();
}

function search(){
    var string = $('input#search').val();
    var rank_filter = [];
    $('input.rank:checked').each(function(){
        rank_filter.push(parseInt($(this).attr('id')));
    })
    var data = {'string': string, 'rank_filter': rank_filter}
    Dajaxice.mw.search(function(result){search_callback(result)}, data);
    $('#enemy_template_list tr:gt(0)').remove();
    $('#getting_started').remove();
    $('#enemy_template_list').show();
    set_template_list_height();
    $('div#searching').show();
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

$(document).ready(function(){
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

    $('#add_template_to_party').click(function(event){
        add_template_to_party(event);
    })

    $('.add_custom_skill').click(function(event){
        add_custom_skill(event);
    })

    $('.add_custom_weapon').click(function(event){
        add_custom_weapon(event);
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
    
    $('img.star').click(function(event){
        toggle_star(event);
    })
    
    $('button#search_button').click(function(event){
        search();
    });
    $('input#search').keyup(function(e){
        if(e.keyCode == 13) search();   // Enter
    });
    
    initialize_enemy_list();
    $('input#search').focus();
    
    $('.natural_weapon').change(function(event){
        $(event.target).parent().parent().find('.ap_hp').toggle();
    });
});