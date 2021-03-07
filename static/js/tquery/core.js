/**
 * tQuery :::: Easy Dynamic Tables
 *
 * ------------ Author: Abid Omar
 *
 * ------------ Support: http://codecanyon.net/user/omarabid
 *
 * ------------ Version: 3.0.0
 *
 * ------------ Date: 8 October 2012
 *
 * ------------ Description: Simple Grid Functionality
 *
 */

/*
 * 
 * JavaScript Functions
 * 
 */

// Convert CSV format to HTML
function csv2html(csv, sep) {
    // Abort operation if null
    if (csv == '') {
        return false;
    }

    // Change delimiter if null
    if (sep == '') {
        sep = ',';
    }

    // split csv string to rows array
    var rows = csv.split('\n');

    // table rows number
    var rows_num = rows.length;

    // Table header
    var column_header = rows[0].split(sep);

    // Table column number
    var column_num = column_header.length;

    // generate the header
    var html = '<thead><tr>';
    for (var i = 0; i < column_num; i++) {
        html = html + '<th>' + column_header[i] + '</th>'
    }
    html = html + '</tr></thead><tbody>';

    // generate the body
    for (var i = 1; i < rows_num; i++) {
        html = html + '<tr>';
        ccol = rows[i].split(sep);
        for (var j = 0; j < column_num; j++) {
            html = html + '<td>' + ccol[j] + '</td>';
        }
        html = html + '</tr>';
    }
    html = html + '</tbody>';

    // Return HTML
    return html;
}

// Draw HTML to object
function drawhtml(data, id) {
    jQuery('#' + id).append(data);
}

/*
 * 
 * jQuery Plugins
 * 
 * 
 */

jQuery.fn.defaultstyle = function (table, tablehead, tablebody, tablecaption) {
    /*
     * Function: defaultstyle Arguments: table, tablehead, tablebody,
     * tablecaption Assign styling to: table, thead tr th, tbody tr td, caption
     */
    jQuery(this).addClass(table);
    jQuery('thead tr th', this).addClass(tablehead);
    jQuery('tbody tr td', this).addClass(tablebody);
    jQuery('caption', this).addClass(tablecaption);
    return this;
}

jQuery.fn.stripped = function (odd) {
    /*
     * Function: stripped Arguments: odd Assign "odd" class to "tbody tr td"
     */
    jQuery('tbody tr', this).children().removeClass(odd);
    jQuery('tbody tr:even', this).each(function () {
        var td = jQuery(this).children();
        jQuery(td).addClass(odd);

    });
    return this;
}

jQuery.fn.headhover = function (headhover, headtdhover) {
    /*
     * Function: headhover Arguments: headhover, headtdhover Assign styling to
     * headhover -> thead tr th headtdhover -> the following tbody tr td
     */
    var tid = this;
    jQuery('thead tr th', this).hover(function () {
        jQuery(this).addClass(headhover);
        // Make the Head Inselectable
        jQuery(this).attr('unselectable', 'on').css('user-select', 'none').css(
            '-moz-user-select', 'none').css('-khtml-user-select', 'none');
        var ind = jQuery(this).index() + 1;
        jQuery(tid).find('td').filter(':nth-child(' + ind + ')')
            .addClass(headtdhover);
    }, function () {
        var ind = jQuery(this).index() + 1;
        jQuery(this).removeClass(headhover);
        jQuery(tid).find('td').filter(':nth-child(' + ind + ')')
            .removeClass(headtdhover);
    });
    return this;
}

jQuery.fn.bodyhover = function (bodyhover) {
    var tid = this;

    jQuery('tbody tr', tid).hover(function () {
        cells = jQuery(this).children();
        cells.addClass(bodyhover);
    }, function () {

        cells.removeClass(bodyhover);
    });
}

jQuery.fn.highlight = function (style) {
    tid = this;
    // highlight on Hover
    jQuery('tbody tr td', this).hover(function () {
        jQuery(this).addClass(style);
    }, function () {
        jQuery(this).removeClass(style);
    });
}

jQuery.fn.clicklight = function (style) {
    // Highlight on click
    jQuery('tbody tr td:not(.numcx)').toggle(function () {
        // Find same cells
        tid = jQuery(this).parent('tr').parent('tbody').parent('table');
        tid2 = '#' + jQuery(tid).attr('id');
        jQuery(tid2).clearstyle(style);
        var simcells = jQuery(tid).searchstrict(jQuery
            .trim(jQuery(this).text()));
        jQuery.each(simcells, function (i, val) {
            simcells[i].addClass(style);
        });

    }, function () {
        tid = jQuery(this).parent('tr').parent('tbody').parent('table');
        var simcells = jQuery(tid).searchstrict(jQuery
            .trim(jQuery(this).text()));
        jQuery.each(simcells, function (i, val) {
            simcells[i].removeClass(style);
        });

    });
}

jQuery.fn.num = function (numclass) {
    // var nss = this.style.num_class;
    var x = 1;
    jQuery('thead tr', this)
        .prepend('<th class="numcx" style="border:hidden"></th>');
    jQuery('tbody tr:not(".removed")', this).each(function () {
        jQuery(this).prepend('<td class="numcx ' + numclass + '">' + x
            + '</td>');
        x++;
    });
    return this;
}

jQuery.fn.renum = function (numclass) {
    // Remove old numeration
    jQuery('.numcx', this).remove();
    jQuery(this).num(numclass);
}

jQuery.fn.sortcolumn = function (column, columnstyle, reverseorder, stype) {
    var tid = this;
    // alert(column);
    var rows = jQuery(this).find('tbody > tr').get();
    jQuery.each(rows, function (index, row) {
        row.sortkey = jQuery(row).children('td').eq(column).text()
            .toUpperCase();
    });
    if (stype == 'date') {
        jQuery.each(rows, function (index, row) {
            row.sortkey = Date.parse(row.sortkey);
        });
    } else if (stype == 'digit') {
        jQuery.each(rows, function (index, row) {
            row.sortkey = parseFloat(row.sortkey.toString().replace(
                /^[^\d.]*/, ''));
        });

    }

    rows.sort(function (a, b) {
        if (a.sortkey > b.sortkey) {
            if (reverseorder == true) {
                return -1;
            }
            return 1;
        }
        if (a.sortkey < b.sortkey) {
            if (reverseorder == true) {
                return 1;
            }
            return -1;
        }
        return 0;
    });
    jQuery.each(rows, function (ind, row) {
        jQuery(tid).children('tbody').append(row);
    });
    jQuery('tbody tr td', this).removeClass(columnstyle);
    jQuery(this).find('td').filter(':nth-child(' + (column + 1) + ')')
        .addClass(columnstyle);
    return this;
}

jQuery.fn.sortall = function () {
    jQuery('thead tr th', this).addClass('sort-alpha');
    return this;
}

jQuery.fn.sort = function (columnstyle, clickablestyle, sortasc, sortdesc, onclickstyle, odd, num, resetnum, numclass, pagination, rowperpage) {
    var tid = this;
    var id = tid.attr('id');
    // Style
    jQuery('thead tr th:not(".numcx")', tid).addClass(clickablestyle);
    jQuery('thead tr th:not(".numcx")', tid)
        .append('<img src="" class="sort-img" />');
    jQuery('thead tr th:not(".numcx") img', tid).css('visibility', 'hidden');
    var upimage = '/static/js/tquery/images/up.png';
    var downimage = '/static/js/tquery/images/down.png';
    jQuery('thead tr th:not(".numcx")', this).mousedown(function () {
        jQuery(this).addClass(onclickstyle)

    }).mouseup(function () {
            jQuery(this).removeClass(onclickstyle);
        }).mouseout(function () {
            jQuery(this).removeClass(onclickstyle);
        });
    // Sort Function
    jQuery('thead tr th:not(".numcx")', this).click(function () {

        // TH index
        var ind = jQuery(this).index();
        // Used to alternate sorting + styles
        var redirect = false;
        // Remove imgs
        jQuery('thead tr th:not(".numcx") img', tid)
            .css('visibility', 'hidden');
        // sorting type
        var stype = 'alpha';
        if (jQuery(this).is('.' + sortasc)) {
            redirect = true;
        } else {
        }
        if (jQuery(this).is('.sort-alpha')) {
            stype = 'alpha';
        }
        if (jQuery(this).is('.sort-digit')) {
            stype = 'digit';
        }
        if (jQuery(this).is('.sort-date')) {
            stype = 'date';
        }
        jQuery(tid).sortcolumn(ind, columnstyle, redirect, stype);

        // Remove all sortth classes
        jQuery(tid).find('th:not(".numcx")').removeClass(sortasc)
            .removeClass(sortdesc);
        // Alternate redirect
        if (redirect == true) {
            jQuery(this).addClass(sortdesc);
            jQuery('img', this).attr('src', upimage).css('visibility',
                'visible');
        } else {
            jQuery(this).addClass(sortasc);
            jQuery('img', this).attr('src', downimage).css('visibility',
                'visible');
        }
        // Reset alternative colors
        jQuery(tid).stripped(odd)
        // Reset Num
        if (resetnum == true & num == true) {
            jQuery(tid).renum(numclass);
        }
        if (pagination == true) {
            jQuery(tid).limit(1, rowperpage);
            jQuery('.pagination.' + id).children('#pag-btn')
                .children('.page-list').children('.page-item').eq(0)
                .addClass('selected-page-item').siblings()
                .removeClass('selected-page-item');
        }
    });

}

jQuery.fn.limit = function (currentpage, rowperpage) {
    var max = Math.ceil(jQuery(this).tableinfo().virtual_rows / rowperpage);
    // Return false if outside limits

    if (currentpage > max) {

        return false;
    }
    // Display the selected part
    jQuery(this).each(function () {
        jQuery(this).find('tbody tr:not(".removed")').show();
        x = (currentpage - 1) * rowperpage;
        y = (currentpage) * rowperpage - 1;
        jQuery(this).find('tbody tr:lt(' + x + ')').hide();
        jQuery(this).find('tbody tr:gt(' + y + ')').hide();
    });
    return this;
}

jQuery.fn.delimit = function () {
    jQuery(this).find('tbody tr').show();
    return this;
}

jQuery.fn.showpagination = function (rowperpage, divid) {
    tid = this;
    id = tid.attr('id');
    current = '.pagination.' + id;
	jQuery(current).remove();
    // Draw pagination after the table
    var rows = jQuery(this).tableinfo().virtual_rows;
    if (rows > rowperpage) {
        var max = Math.ceil(rows / rowperpage);
        jQuery(tid).after('<div class="pagination ' + id + '" idd="' + id
            + '"></div>');
        jQuery(current).append('<div class="pag-info">Showing 1 - ' + rowperpage
            + ' of ' + rows + '</div>');
        jQuery(current)
            .append('<div id="pag-btn"><ul class="page-list"></ul></div>');
        for (var x = 1; x < 4; x++) {
            if (x > max) {
                break;
            }
            jQuery(current).children('#pag-btn').children('.page-list')
                .append('<li class="page-item" id="' + x + '">' + x
                + '</li>');

        }
        // If more than 8 pages
        if (max > 8) {
            jQuery(current).children('#pag-btn').children('.page-list')
                .append('<li class="page-item" id="0">...</li>');
            for (var x = max - 2; x < max + 1; x++) {
                jQuery(current).children('#pag-btn').children('.page-list')
                    .append('<li class="page-item" id="' + x + '">' + x
                    + '</li>');
            }
        } else if (max > 3) {
            for (var x = 3; x < max + 1; x++) {
                jQuery(current).children('#pag-btn').children('.page-list')
                    .append('<li class="page-item" id="' + x + '">' + x
                    + '</li>');

            }
        }
        // First limitation

        jQuery(tid).limit(1, rowperpage);
        jQuery(current).children('#pag-btn').children('.page-list')
            .children('.page-item').eq(0).addClass('selected-page-item');
        // On click

        jQuery('.page-item').live('click', function () {
            var idd = jQuery(this).parent('.page-list').parent('#pag-btn')
                .parent('.pagination').attr('idd');

            var tid = '#' + idd,
                page = jQuery(this).attr('id');
            if (page != 0) {

                jQuery(tid).limit(page, rowperpage);
                jQuery(this).addClass('selected-page-item').siblings()
                    .removeClass('selected-page-item');
                var dmax = page * rowperpage;
                if (dmax > rows) {
                    dmax = rows;
                }
                jQuery('.pag-info', '.' + idd).html('Showing '
                    + (((page - 1) * rowperpage) + 1) + ' - ' + dmax
                    + ' of ' + rows);
            } else {
                cr = jQuery('.page-list.selected-page-item').index();
                jQuery('.page-list').empty();
                for (var x = 1; x < max + 1; x++) {
                    jQuery('.page-list').append('<li class="page-item" id="'
                        + x + '">' + x + '</li>');
                }
                jQuery('.page-item').eq(cr).addClass('selected-page-item');

            }
        });
    }
}

jQuery.fn.editablecell = function (clicklight, style, hstyle, bstyle) {
    tid = this;
    // Bind Double Click
    jQuery('tbody tr td:not(.numcx)', this).bind('dblclick', edit);
    // Bind buttons
    jQuery('.save').live('click', save);
    jQuery('.del').live('click', del);
    // Function edit
    function edit() {

        var old = jQuery.trim(jQuery(this).html().replace(/"/g, "&quot;"));
        jQuery(this)
            .html('')
            .html('<form><input old="'
            + old
            + '" type="text" class="editcell" value="'
            + old
            + '" /><ul class="btn"><li ><a class="save">Save</a></li><li> <a class="del">Discard</a></li></ul></form>')
            .unbind('dblclick').unbind('click');

    }

    function save() {
        var elm = jQuery(this).parents('form');
        var newtext = jQuery('.editcell', elm).val();
        var scop1 = this;

        /*
         * TODO: Change Clone Copy
         *
         */

        var tdn = jQuery(scop1).parents('td').index();
        var trn = jQuery(scop1).parents('td').parent();
        var trnid = trn.attr('id');

        /*
         * TODO
         *
         */
        jQuery(scop1).parents('td').html('').html(newtext).bind('dblclick',
            edit);
        // remove clicklighting style
        if (clicklight == true) {
            jQuery(tid).clicklight(style);
        }
        // Rebind buttons events
        jQuery('.save').bind('click', save);
        jQuery('.del').bind('click', del);
        // Remove highlighting style
        jQuery('tbody tr td', tid).removeClass(hstyle);
        jQuery('tbody tr td', tid).removeClass(bstyle);
    }

    function del() {
        var elm = jQuery(this).parents('form');
        var newtext = jQuery('.editcell', elm).attr('old');
        jQuery(this).parents('td').html('').html(newtext)
            .bind('dblclick', edit);
        // remove clicklighting style
        if (clicklight == true) {
            jQuery(tid).clicklight(style);
        }
        // Rebind buttons events
        jQuery('.save').bind('click', save);
        jQuery('.del').bind('click', del);
        // Remove highlighting style
        jQuery('tbody tr td', tid).removeClass(hstyle);
        jQuery('tbody tr td', tid).removeClass(bstyle);
    }

}

jQuery.fn.clearstyle = function (style) {
    jQuery(this).find('*').removeClass(style);
    return this;
}

jQuery.fn.searchstrict = function (query) {
    var fd = new Array();
    var jQuerysr = jQuery('tbody tr td:contains("' + query + '")', this);
    jQuerysr.each(function (i) {
        if (jQuery.trim(jQuery(this).text()) == query) {
            fd[i] = jQuery(this);
        }
    });
    if (fd[0] == null) {
        return false;
    } else {
        return fd;
    }
}

jQuery.fn.tocsv = function (sep) {
    tid = this;

    var csv = '';

    if (sep == undefined) {
        sep = ',';
    }

    jQuery('thead tr th', tid).each(function () {
        csv = csv + jQuery.trim(jQuery(this).text()) + sep;
    });
    csv = csv.slice(0, -1);
    csv = csv + "\n";
    jQuery('tbody tr', tid).each(function () {
        jQuery(this).children().not('.numcx').each(function () {
            csv = csv + jQuery.trim(jQuery(this).text()) + sep;
        });
        csv = csv.slice(0, -1);
        csv = csv + "\n";
    });

    // Return the CSV
    return csv;
}

jQuery.fn.tableinfo = function () {

    // Column number
    var columns = jQuery('thead tr th', this).size();

    // Virtual Columns
    var virtual_columns = jQuery('thead tr th:not(".removed")', this).size();

    // Rows number
    var rows = jQuery('tbody tr', this).size();

    // Virtual Rows
    var virtual_rows = jQuery('tbody tr:not(".removed")', this).size();

    // Cells number
    var cells = jQuery('tbody tr td', this).size();

    // Virtual Cells
    var virtual_cells = virtual_columns * virtual_rows;

    // Current page
    var current = jQuery('.pagination .selected-page-item', this).index() + 1;

    return {
        'columns':columns,
        'virtual_columns':virtual_columns,
        'rows':rows,
        'virtual_rows':virtual_rows,
        'cells':cells,
        'virtual_cells':virtual_cells,
        'current_page':current
    }
}

/*
 * New Functions (Added in Version 2.0)
 */

// Case Insensitive Contains
jQuery.expr[':'].Contains = function (a, i, m) {
    return jQuery(a).text().toUpperCase().indexOf(m[3].toUpperCase()) >= 0;
};

// Dual Case Search
jQuery.fn.search = function (query, sens) {
    if (sens == true) {
        return jQuery('tbody tr:contains("' + query + '")', this);
    } else {
        return jQuery('tbody tr:Contains("' + query + '")', this);
    }
}
// Inversed Dual Case Search
jQuery.fn.inv_search = function (query, sens) {
    if (sens == true) {
        return jQuery('tbody tr:not(:contains("' + query + '"))', this);
    } else {
        return jQuery('tbody tr:not(:Contains("' + query + '"))', this);
    }
}

// Filter Feature
jQuery.fn.filter_feature = function () {

    // Create the temporary table
    var tid = this;
    var id = tid.attr('id');
    $(tid).before('<table id="temp-' + id + '"><tbody></tbody></table>');
    var tempid = "temp-" + id;
    $('#' + tempid).hide();

    // Assign unique ID to tr
    $('tbody tr', tid).each(function (i, val) {
        $(this).attr('id', i);
    });

    // Clone the whole table
    $('tbody tr', tid).each(function () {
        $(this).clone(true).appendTo('#' + tempid + ' tbody');
    });
}

// filter table
jQuery.fn.filter_table = function (word, sens, num, numclass, pag, rowpag, strip) {
    var tid = this;
    var id = tid.attr('id');
    var tempid = "temp-" + id;
    // Remove All Cells
    $('tbody', tid).remove();
    // Replace all the body
    $('#' + tempid + ' tbody').clone(true).appendTo(tid);
    // Remove Useless Cells
    $(tid).inv_search(word, sens).remove();
    // Remove Pagination
    $('div#' + id + '.pagination').remove();
    // Show hidden TR
    $('tbody tr', tid).show();

    // ReStrip
    jQuery(tid).stripped(strip);
    // Restart Numeration
    if (num == true) {
        $(tid).renum(numclass);
    }
    // Repaginate
    if (pag == true) {
        $(tid).showpagination(rowpag);
    }
    // hide sort image
    $('.sort-img', tid).css('visibility', 'hidden');
}
/*
 * 
 * 
 * Main Class -- This Class is used to store variables -- -- Also used to load
 * table from CSV --
 * 
 */

function ttable(tableid, divid) {
    // Store the table ID
    this.tableid = tableid;

    // Store the Inner Div ID
    this.divid = divid;

    // Table Custom Styling
    this.style = new Object();
    this.style.table = new String;
    this.style.table = 'table-default';
    this.style.tablehead = new String;
    this.style.tablehead = 'head-default';
    this.style.tablebody = new String;
    this.style.tablebody = 'body-default';
    this.style.tablecaption = new String;
    this.style.tablecaption = 'caption-default';

    // Custom Hover Class
    this.style.bodyhover = new Boolean;
    this.style.bodyhover = true;
    this.style.headhover = new Boolean;
    this.style.headhover = true;
    this.style.tablehead_hover = new String;
    this.style.tablehead_hover = 'hoverhead-default';
    this.style.tableheadtd_hover = new String;
    this.style.tableheadtd_hover = 'hoverheadtd-default';
    this.style.tablebody_hover = new String;
    this.style.tablebody_hover = 'hoverbody-default';

    // Highlighting Custom Styling
    this.highlight = new Object();
    this.highlight.enabled = new Boolean;
    this.highlight.enabled = true;
    this.highlight.style = new String;
    this.highlight.style = 'highlight-default';
    this.highlight.onlclick = new Boolean;
    this.highlight.onclick = false;
    this.highlight.onclick_style = new String;
    this.highlight.onclick_style = 'clicklight-default';

    // Stripped Rows Parameters
    this.style.stripped = new Boolean;
    this.style.stripped = true;
    this.style.odd_row = new String;
    this.style.odd_row = 'odd-default';

    // Numeration Parameters
    this.style.num = new Boolean;
    this.style.num = true;
    this.style.num_class = new String;
    this.style.num_class = 'num-default';

    // Sorting Paramters
    this.sorting = new Object();
    this.sorting.enabled = new Boolean;
    this.sorting.enabled = true;
    this.sorting.sortall = new Boolean;
    this.sorting.sortall = false;
    this.sorting.resetnum = new Boolean;
    this.sorting.resetnum = true;
    this.sorting.sortedstyle = new String;
    this.sorting.sortedstyle = 'sorted-default';
    this.sorting.clickablestyle = new String;
    this.sorting.clickablestyle = 'clickable-default';
    this.sorting.onclickstyle = new String;
    this.sorting.onclickstyle = 'onclick-default';
    this.sorting.sortascstyle = new String;
    this.sorting.sortascstyle = 'sortasc-default';
    this.sorting.sortdescstyle = new String;
    this.sorting.sortdescstyle = 'sortdesc-default';

    // Pagination Paramaters
    this.pagination = new Object();
    this.pagination.enabled = new Boolean;
    this.pagination.enabled = false;
    this.pagination.rowperpage = new Number;
    this.pagination.rowperpage = 10;

    // Editable Parameters
    this.edit = new Object();
    this.edit.enabled = new Boolean;
    this.edit.enabled = false;

    // Conversion Parameters
    this.csv = new Object();
    this.csv.separator = new String;
    this.csv.separator = ',';

    // Search Input
    this.search = new Object();
    this.search.enabled = new Boolean;
    this.search.enabled = false;
    this.search.inputID = new String;
    this.search.inputID = "filter";
    this.search.casesensitive = new Boolean;
    // True = Case Sensitive
    this.search.casesensitive = false;

    // Table Information
    this.info = new Object();
}

/*
 * 
 * 
 * Main Class Prototype -- This Class is used to apply effects after checking if
 * they are enabled --
 * 
 * 
 */

ttable.prototype.rendertable = function () {

    var tableid = this.tableid;
    ttid = this;

    // Apply default styling
    jQuery('#' + tableid).defaultstyle(ttid.style.table, ttid.style.tablehead,
        ttid.style.tablebody, ttid.style.caption);

    // Stripped Styling
    if (ttid.style.stripped == true) {
        jQuery('#' + tableid).stripped(ttid.style.odd_row);
    }

    // Apply Head Hover Effect
    if (ttid.style.headhover == true) {
        jQuery('#' + tableid).headhover(ttid.style.tablehead_hover,
            ttid.style.tableheadtd_hover);
    }

    // Apply Body Hover Effect
    if (ttid.style.bodyhover == true) {
        jQuery('#' + tableid).bodyhover(ttid.style.tablebody_hover);
    }

    // Apply Highlighting
    if (ttid.highlight.enabled == true) {
        jQuery('#' + tableid).highlight(ttid.highlight.style);
    }

    // Apply Click lighting
    if (ttid.highlight.onclick == true) {
        jQuery('#' + tableid).clicklight(ttid.highlight.onclick_style);
    }

    // Apply numeration
    if (ttid.style.num == true) {
        jQuery('#' + tableid).num(ttid.style.num_class);
    }

    // Apply Sorting
    if (ttid.sorting.enabled == true) {
        if (ttid.sorting.sortall == true) {
            jQuery('#' + tableid).sortall();
        }
        jQuery('#' + tableid).sort(ttid.sorting.sortedstyle,
            ttid.sorting.clickablestyle, ttid.sorting.sortascstyle,
            ttid.sorting.sortdescstyle, ttid.sorting.onclickstyle,
            ttid.style.odd_row, ttid.style.num, ttid.sorting.resetnum,
            ttid.style.num_class, ttid.pagination.enabled,
            ttid.pagination.rowperpage);
    }

    // Add Pagination
    if (ttid.pagination.enabled == true) {
        jQuery('#' + tableid).showpagination(ttid.pagination.rowperpage,
            ttid.divid);
    }

    // Add Editing
    if (ttid.edit.enabled == true) {
        jQuery('#' + tableid).editablecell(ttid.highlight.onclick,
            ttid.highlight.onclick_style, ttid.highlight.style,
            ttid.style.tablebody_hover);
    }

    // Activate Search
    if (ttid.search.enabled == true) {
        // Prepare the table for the search feature
        $('#' + tableid).filter_feature();
        // link the textbox
        var inputID = ttid.search.inputID;
        var sens = ttid.search.casesensitive;
        var num = ttid.style.num;
        var num_class = ttid.style.num_class;
        var pagination = ttid.pagination.enabled;
        var rowperpage = ttid.pagination.rowperpage;
        var strip = ttid.style.odd_row;
        $('#' + inputID).keyup(function (event) {
            if (event.keyCode == 13){
                var word = $(this).val();
                $('#' + tableid).filter_table(word, sens, num, num_class, pagination, rowperpage, strip);
            }
        });

    }
    // Populate the information object
    ttid.info = jQuery('#' + tableid).tableinfo();
}

ttable.prototype.loadcsv = function (url) {
    ths = this;
    tid = '#' + this.tableid;
    sep = this.csv.separator;
    jQuery.get(url, function (data) {
        html = csv2html(data, sep);
        jQuery(tid).prepend(html);
        ths.rendertable();
    });

}