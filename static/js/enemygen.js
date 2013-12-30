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

function capitalize(string){
    return string.charAt(0).toUpperCase() + string.slice(1);
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
    
});