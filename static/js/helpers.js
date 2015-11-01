function submit_callback(result, input_object){
    if (result.success){
        $('#commit_result').html('Save successful');
        animate_background(input_object, true);
    } else {
        if (input_object && input_object.type == 'checkbox'){
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
    var color;
    if (success) {
        color = 'green';
    } else {
        color = 'red';
    }
	item.css('background', color)
	item.animate({backgroundColor: 'white'}, 3000);
}

function refresh_page(result){
    location.reload();
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

function capitalize(string){
    return string.charAt(0).toUpperCase() + string.slice(1);
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

    $('input.enemy_amount').keyup(bind_amount_listeners);
    $('input.enemy_amount').change(bind_amount_listeners);

    if ($('#enemy_template_list tr').length < 2){
        $('#enemy_template_list').hide();
    }
}

function bind_amount_listeners(event){
    /* Binds the listeners of for the amount fields for the dynamically created enemy rows on home page */
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
}

