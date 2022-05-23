
console.log("javascript is working...");


var startdate = $("#startdate");
var date = new Date(new Date().getTime() - (1000 * 60 * 60 * 24 * 30));
startdate.val(date.toISOString().substr(0, 10));

var enddate = $("#enddate");
date = new Date();
enddate.val(date.toISOString().substr(0, 10));


var queryString = window.location.search;
var urlParams = new URLSearchParams(queryString);
var pr = {{ pr.pk }} //urlParams.get('pr')
console.log(pr);
var filename = "";
var popupNode = document.createElement("div");
popupNode.style.border = '2px solid grey'
popupNode.style.padding = '5px'
popupNode.style.background = 'white'
popupNode.style.color = 'black';
popupNode.style.zIndex = '9999';


//Setup our fancy textarea with highlighting ability
/*$("#dochelper").on({
    'input': handleInput,
    'scroll': handleScroll
});
function handleInput() {
    var text = $("#dochelper").val();
    //console.log( text );
    var highlightedText = applyHighlights(text);
    $("#highlightsdiv").html(highlightedText);
}
function applyHighlights(text) {

    //return text
    //  .replace(/\n$/g, '\n\n')
    //  .replace(/[A-Z].*?\b/g, '<mark>$&</mark>');

    text = text.replace(/\n$/g, '\n\n');
    //[(215, 220), (813, 818)]
    //text = [text.slice(0, 818), "</mark>", text.slice(818)].join('');
    //text = [text.slice(0, 813), "<mark>", text.slice(813)].join('');
    //text = [text.slice(0, 220), "</mark>", text.slice(220)].join('');
    //text = [text.slice(0, 215), "<mark>", text.slice(215)].join('');
    text = text.replaceAll('round:','<mark>round</mark>:')
    text = text.replaceAll('round=','<mark>round</mark>=')

    console.log( text );
    return text
}
function handleScroll() {
    var scrollTop = $("#dochelper").scrollTop();
    $(".backdrop").scrollTop(scrollTop);
}
handleInput();*/

var editor = CodeMirror.fromTextArea(document.getElementById("dochelper"), {
    lineNumbers: true,
    mode: "text/x-python", //"text/x-c++src", //"text/html",
    matchBrackets: true,
    spellcheck: true,
    autocorrect: true,
    styleSelectedText: true
});


function showDocEditor(docfilename, difftext) {

    console.log("TEST");
    console.log(difftext);

    filename = docfilename;

    $('#dochelpertitle').html(filename);

    //$('#dochelper').empty();

    $.ajax({
        url: '/dashboard/getfile/', type: 'POST', data: { 'pr': pr, 'filename': filename }, success: function (result) {
            console.log("get file contents");
            console.log(result);


            editor.setValue(result['filecontents']);

            editor.markText({ line: 4, ch: 9 }, { line: 4, ch: 24 }, { className: "styled-background" });
            editor.markText({ line: 6, ch: 12 }, { line: 6, ch: 22 }, { className: "styled-background" });

            editor.on("cursorActivity", function () {

                var cursor = editor.getCursor();

                if (cursor.line == 4 && cursor.ch >= 9 && cursor.ch <= 24) {
                    var text = document.createTextNode("We can say a bunch of stuff about why this is highlighted right here.");
                    popupNode.innerHTML = '';
                    popupNode.appendChild(text);
                    editor.addWidget({ line: 4, ch: 9 }, popupNode, true);
                } else {
                    popupNode.remove();
                }
            });


            setTimeout(function () {
                editor.refresh();
            }, 1);

            $('#docModal').modal('show');
        }
    });

}


function patchFile() {

    console.log(editor.getValue());


    $.ajax({
        url: '/dashboard/createpatch/', type: 'POST', data: { 'pr': pr, 'filename': filename, 'filecontents': editor.getValue() }, success: function (result) {

            console.log("success ajax");
            console.log(result);

            var element = document.createElement('a');
            element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(result.patch));
            element.setAttribute('download', result.filename);

            element.style.display = 'none';
            document.body.appendChild(element);

            element.click();

            document.body.removeChild(element);
        }
    });

}


function loadPatternGraph() {
    console.log("Rerunning pattern graph...");

    $('#patterngraph1').hide();
    $('#patternlabel1').show();

    $.ajax({
        url: '/dashboard/patterngraph1', data: { 'pr': pr, 'start': $("#startdate").val(), 'end': $("#enddate").val() }, success: function (result) {
            console.log("success pattern");
            console.log(result);

            $('#patterngraph1').attr('src', '/media/figures/' + result['filename']);
            $('#patternlabel1').hide();
            $('#patterngraph1').show();


        }
    });
}


$.ajaxSetup({
    beforeSend: function (xhr, settings) {
        xhr.setRequestHeader("X-CSRFToken", "{{csrf_token}}");
    }
})

console.log("PR");
console.log(pr);

$.ajax({
    url: '/dashboard/diffcommitdata/', type: 'POST', data: { 'pr': pr }, success: function (result) {
        console.log("success diff commits");
        console.log(result);

        var table = $("#diffcommittable > tbody");
        table.empty();

        var doctable = $("#docdiffcommittable > tbody");
        doctable.empty();

        for (var i = 0; i < result['diffcommits'].length; i++) {
            var commits = "";
            var diffs = "";
            var doccommits = "";
            var docdiffs = "";
            for (var j = 0; j < result['diffcommits'][i]['commits'].length; j++) {

                var diff = result['diffcommits'][i]['commits'][j]['diff'];
                var diffadds = (diff.charAt(0) == '+' ? 1 : 0);
                var diffsubs = (diff.charAt(0) == '-' ? 1 : 0);

                diffadds += (diff.match(/\n\+/g) || []).length;
                diffsubs += (diff.match(/\n\-/g) || []).length;

                commits += "<a target='_blank' href='{{pr.project.source_url|slice:"0: -4"}}/commit/" + result['diffcommits'][i]['commits'][j]['commit'] + "'>" + result['diffcommits'][i]['commits'][j]['commit'].substring(0, 7) + "</a><br/>";


                diff = diff.replace(/&/g, '&amp;').replaceAll('\"', '&quot;').replaceAll('\'', '&lsquo;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                diffs += "<span data-bs-toggle='popover' data-bs-trigger='hover' data-bs-html='true' data-bs-placement='left' data-bs-content='<pre>" + diff.substring(0, Math.min(diff.length, 1000)) + "</pre>'>" + diffadds + "&nbsp;adds,&nbsp;" + diffsubs + "&nbsp;subs</span><br/>";

                //see if we should add commit to doc file table
                for (var k = 0; k < result['prcommits'].length; k++) {
                    if (result['diffcommits'][i]['commits'][j]['commit'] == result['prcommits'][k]['hash']) {
                        doccommits += "<a target='_blank' href='{{pr.project.source_url|slice:"0: -4"}}/commit/" + result['diffcommits'][i]['commits'][j]['commit'] + "'>" + result['diffcommits'][i]['commits'][j]['commit'].substring(0, 7) + "</a><br/>";
                        docdiffs += "<button class='btn btn-xs btn-primary' onclick='showDocEditor(\"" + result['diffcommits'][i]['filename'] + "\",\"" + "DIFF STUFF TO GO HERE" + "\");'>View Docs</button><br/>";

                    }
                }

            }

            table.append("<tr><td>" +
                result['diffcommits'][i]['filename'] +
                "</td><td>" +
                commits +
                "</td><td>" +
                diffs +
                "</td></tr>");

            doctable.append("<tr><td>" +
                result['diffcommits'][i]['filename'] +
                "</td><td>" +
                doccommits +
                "</td><td>" +
                docdiffs +
                "</td></tr>");

        }

        $('.popover-dismiss').popover({ trigger: 'focus' });

        //$(function() {
        //	$('[data-bs-toggle="popover"]').popover();
        //});

        setTimeout(function () {
            $('[data-bs-toggle="popover"]').popover();
        }, 1000);


    }
});


$.ajax({
    url: '/dashboard/patterngraph1', data: { 'pr': pr }, success: function (result) {
        console.log("success pattern");
        console.log(result);

        $('#patterngraph1').attr('src', '/media/figures/' + result['filename']);
        $('#patternlabel1').hide();
        $('#patterngraph1').show();


    }
});


$.ajax({
    url: '/dashboard/branchdata', data: { 'test': 'test' }, success: function (result) {
        console.log("success");
        console.log(result);

        $('#open_branches').html(result['open_branches'].join(' '));
        $('#feature_branches').html(result['feature_branches'].join(' '));
        $('#created_branches').html(result['created_branches'].join(' '));
        $('#deleted_branches').html(result['deleted_branches'].join(' '));


        var table = $('#branches_table > tbody:last-child');

        for (var i = 0; i < result['name_column'].length; i++) {
            console.log(result['name_column'][i]);
            table.append('<tr><td>' + result['name_column'][i] + '</td><td>' + result['author_column'][i] + '</td><td>' + result['created_column'][i] + '</td><td>' + result['deleted_column'][i] + '</td></tr>');
        }


    }
});
