function submit(id, type, input_object, value, parent_id){
	//Called when a field is changed
    (function(value, id, type, input_object){
        Dajaxice.enemygen.submit(function(result) {submit_callback(result, input_object)}, {'value': value, 'id': id, 'object': type, 'parent_id': parent_id});
    })(value, id, type, input_object);
}

function submit_callback(result, input_object){
    console.log(result.error)
    console.log(result.message);
    if (result.success){
        $('#commit_result').html('Save successful');
        animate_background(input_object, true);
    } else {
        $(input_object).val(result.original_value);
        animate_background(input_object, false);
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

function add_custom_spell(event){
    var type = $(event.target).attr('type');
    var et_id = $(event.target).attr('et_id');
    Dajaxice.enemygen.add_custom_spell(add_custom_spell_callback, {'type': type, 'et_id': et_id})
}

function add_custom_spell_callback(result){
    location.reload();
}

$(document).ready(function(){

	$('.data:input[type=number], .data:input[type=text], select.data').blur(function(event){
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
	
});