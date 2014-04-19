function submit(id, type, input_object, value, parent_id){
	//Called when a field is changed
    (function(value, id, type, input_object){
        Dajaxice.enemygen.submit(function(result) {submit_callback(result, input_object)}, {'value': value, 'id': id, 'object': type, 'parent_id': parent_id});
    })(value, id, type, input_object);
}

function submit_callback(result, input_object){
    if (result.success){
        $('#commit_result').html('Save successful');
        animate_background(input_object, true);
    } else {
        if (input_object.type == 'checkbox'){
            $(input_object).prop('checked', result.original_value);
        } else {
            $(input_object).val(result.original_value);
            animate_background(input_object, false);
        }
        console.log(result.error)
        console.log(result.message);
    }
}

function bind_change_listeners(event){
	var original_value = $(event.target).data("default_value");
	if (event.target.type == 'checkbox') {
		var new_value = event.target.checked;
	} else {
		var new_value = $(event.target).val();
	}
	if (new_value != original_value){
		var item_id = $(event.target).attr('item_id');
		var parent_id = $(event.target).attr('parent_id');
		var item_type = $(event.target).attr('item_type');
		submit(item_id, item_type, event.target, new_value, parent_id)
	}
}

function animate_background(selector, success){
	var item = $(selector);
	var original_background = item.css('background');
    var color;
    if (success) {
        color = 'green';
    } else {
        color = 'red';
    }
	item.css('background', color)
	item.animate({backgroundColor: original_background}, 3000);
}

function add_custom_skill(event){
    var et_id = $(event.target).attr('et_id');
    Dajaxice.enemygen.add_custom_skill(refresh_page, {'et_id': et_id})
}

function add_additional_feature(event){
    var parent_id = $(event.target).attr('parent_id');
    var type = $(event.target).attr('object_type');
    var feature_list_id = $('#additional_feature_options').val();
    Dajaxice.enemygen.add_additional_feature(refresh_page, {'parent_id': parent_id, 'feature_list_id': feature_list_id, 'type': type})
}

function add_custom_spell(event){
    var type = $(event.target).attr('type');
    var et_id = $(event.target).attr('et_id');
    Dajaxice.enemygen.add_custom_spell(refresh_page, {'type': type, 'et_id': et_id})
}

function add_spirit(event){
    var spirit_ids = $('#spirit_options').val();
    var et_id = $(event.target).attr('et_id');
    Dajaxice.enemygen.add_spirit(refresh_page, {'spirit_ids': spirit_ids, 'et_id': et_id})
}

function add_cult(event){
    var cult_ids = $('#cult_options').val();
    var et_id = $(event.target).attr('et_id');
    Dajaxice.enemygen.add_cult(refresh_page, {'cult_ids': cult_ids, 'et_id': et_id})
}

function add_template_to_party(event){
    var template_ids = $('#template_ids').val();
    var party_id = $(event.target).attr('party_id');
    Dajaxice.enemygen.add_template_to_party(refresh_page, {'template_ids': template_ids, 'party_id': party_id})
}

function add_custom_weapon(event){
    var type = $(event.target).attr('type');
    var cs_id = $(event.target).attr('cs_id');
    Dajaxice.enemygen.add_custom_weapon(refresh_page, {'type': type, 'cs_id': cs_id})
}

function add_hit_location(event){
    var race_id = $(event.target).attr('race_id');
    Dajaxice.enemygen.add_hit_location(refresh_page, {'race_id': race_id})
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

function add_nonrandom_feature(event){
    var et_id = $(event.target).attr('et_id');
    var party_id = $(event.target).attr('party_id');
    var feature_id = $('#nonrandom_feature_options').val()
    if (et_id) {
        Dajaxice.enemygen.add_nonrandom_feature(refresh_page, {'et_id': et_id, 'feature_id': feature_id})
    } else if (party_id) {
        Dajaxice.enemygen.add_nonrandom_feature(refresh_page, {'party_id': party_id, 'feature_id': feature_id})
    }
}

function del_item(event){
    var item_id = $(event.target).attr('item_id');
    var item_type = $(event.target).attr('item_type');
    Dajaxice.enemygen.del_item(refresh_page, {'item_id': item_id, 'item_type': item_type})
}

function deltag_submit(id, type, input_object, value){
    (function(value, id, type, input_object){
        Dajaxice.enemygen.submit(function(result) {deltag_callback(result, input_object)}, {'value': value, 'id': id, 'object': type, 'parent_id': null});
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

function apply_notes_to_templates(event){
    var race_id = $(event.target).attr('item_id');
    var notes = $('#race_notes').html();
    Dajaxice.enemygen.apply_notes_to_templates(apply_notes_to_templates_callback, {'race_id': race_id, 'notes': notes});
}

function refresh_page(result){
    location.reload();
}

function apply_notes_to_templates_callback(result){
    if (result.success){
        $('#apply_notes_to_templates_confirmation').show();
        setTimeout(function(){$('#apply_notes_to_templates_confirmation').fadeOut(1000);}, 3000);
    } else {
        console.log(result);
    }
}

function toggle_star_callback(result, target){
    var target = $(target);
    if (result.success){
        if (target.attr('src') === '/rq_static/images/star_filled.png'){
            target.attr('src', '/rq_static/images/star_empty.png');
        } else {
            target.attr('src', '/rq_static/images/star_filled.png');
        }
    }
}

function toggle_star(event){
    var et_id = $(event.target).attr('et_id');
    Dajaxice.enemygen.toggle_star(function(result){toggle_star_callback(result, event.target)}, {'et_id': et_id});
}

function capitalize(string){
    return string.charAt(0).toUpperCase() + string.slice(1);
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

function search(){
    var string = $('input#search').val();
    Dajaxice.enemygen.search(function(result){search_callback(result)}, {'string': string});
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

function initialize_enemy_list(){
    $('#temp-enemy_template_list').remove();    // In case it exists, delete the existing temp table
    var table = new ttable('enemy_template_list'); 
    table.sorting.enabled = true;
    table.sorting.sortall = false;
    table.search.enabled = true;
    table.search.inputID = 'searchinput';
    table.search.casesensitive = false;
    table.style.num = false;
    //$('img.sort-img').remove(); // Each time rendertable is called, new set of sort images are added
    table.rendertable();
    
    set_template_list_height();
    $(window).resize(function(event){
        set_template_list_height();
    });
    
    $('input.enemy_amount').keyup(function(event){
        var amount = $(event.target).val();
        if (amount > 0) {
            var input_id = $(event.target).attr('id');
            var row_id = $(event.target).parent().parent().attr('id');
            var row = $(event.target).parent().parent().remove().clone(); //tr -element
            $('#selected_enemy_template_list').append(row);
            // Need to delete it also from the temp table created by the sorter
            $('table#temp-enemy_template_list').find('tr#'+row_id).remove();
            $('#selected_enemy_template_list_container').show(0);
            var val = $('#'+input_id).val();
            $('#'+input_id).focus().val('').val(val);
            set_column_width();
            set_template_list_height();
            $('#generate_button').removeClass('disabled');
            $('#generate_button').prop('disabled', false);
        }
    });
    
    if ($('#enemy_template_list tr').length < 2){
        $('#enemy_template_list').hide();
    }
    
}

$(document).ready(function(){
	$('.data:input[type=number], .data:input[type=text], select.data, textarea.data').blur(function(event){
		bind_change_listeners(event);
	});

	$('input.data:checkbox').change(function(event){
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
    
    initialize_enemy_list();
    $('input#search').focus();
});