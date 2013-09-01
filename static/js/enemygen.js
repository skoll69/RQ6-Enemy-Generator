function submit(id, type, input_object, value, parent_id){
	//Called when a field is changed
    (function(value, id, type, input_object){
        Dajaxice.enemygen.submit(function(result) {submit_callback(result, input_object)}, {'value': value, 'id': id, 'object': type, 'parent_id': parent_id});
    })(value, id, type, input_object);
}

function submit_callback(result, input_object){
    //console.log(result.error)
    //console.log(result.message);
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

function add_custom_spell(event){
    var type = $(event.target).attr('type');
    var et_id = $(event.target).attr('et_id');
    Dajaxice.enemygen.add_custom_spell(refresh_page, {'type': type, 'et_id': et_id})
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

function del_hit_location(event){
    var hl_id = $(event.target).attr('hl_id');
    Dajaxice.enemygen.del_hit_location(refresh_page, {'hl_id': hl_id})
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

    $('.add_custom_skill').click(function(event){
        add_custom_skill(event);
    })

    $('.add_custom_weapon').click(function(event){
        add_custom_weapon(event);
    })
    
    $('#add_hit_location').click(function(event){
        add_hit_location(event);
    })
    
    $('.del_hit_location').click(function(event){
        del_hit_location(event);
    })
    
    $('#apply_notes_to_templates').click(function(event){
        apply_notes_to_templates(event);
    })
    
});