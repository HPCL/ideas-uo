console.log("javascript is working...");


var startdate = $("#startdate");
var date = new Date(new Date().getTime() - (1000 * 60 * 60 * 24 * 30));
startdate.val(date.toISOString().substr(0, 10));

var enddate = $("#enddate");
date = new Date();
enddate.val(date.toISOString().substr(0, 10));


var queryString = window.location.search;
var urlParams = new URLSearchParams(queryString);
var pr = $("#pr").val(); //urlParams.get('pr') //{{ pr.pk }}
console.log("The PR id...");
console.log($("#pr"));
console.log(pr);
var filename = "";
var popupNode = document.createElement("div");
popupNode.style.border = '2px solid grey'
popupNode.style.padding = '5px'
popupNode.style.background = 'white'
popupNode.style.color = 'black';
popupNode.style.zIndex = '9999';

let csrf_token = document.querySelector('[name=csrfmiddlewaretoken]').value;

var editor = CodeMirror.fromTextArea(document.getElementById("dochelper"), {
    lineNumbers: true,
    mode: "text/x-python", //"text/x-c++src", //"text/html",
    matchBrackets: true,
    spellcheck: true,
    autocorrect: true,
    styleSelectedText: true
});

var cqeditor = CodeMirror.fromTextArea(document.getElementById("cqhelper"), {
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

            //editor.markText({ line: 3, ch: 0 }, { line: 3, ch: 13 }, { className: "styled-background" });
            //editor.markText({ line: 6, ch: 12 }, { line: 6, ch: 22 }, { className: "styled-background" });
            //editor.markText({ line: 4, ch: 2 }, { line: 4, ch: 6 }, { className: "styled-background" });

            //for(var i=0; i<result['linter_results'].length; i++){
            //    editor.markText({ line: result['linter_results'][i].line-1, ch: result['linter_results'][i].column }, { line: result['linter_results'][i].line-1, ch: 100 }, { className: "styled-background" });
            //}

            for(var i=0; i<result['docstring_results'][1].length; i++){

                if( result['docstring_results'][1][i][0] == filename ){
                    for(var j=0; j<result['docstring_results'][1][i][1].length; j++){

                        if( result['docstring_results'][1][i][1][j].result.length > 0 ){  
                            console.log("MARK LINE: " + result['docstring_results'][1][i][1][j].result[0][1] );                      
                            editor.markText({ line: result['docstring_results'][1][i][1][j].result[0][1], ch: 0 }, { line: result['docstring_results'][1][i][1][j].result[0][1], ch: 100 }, { className: "styled-background" });
                        }
                    }
                }
            }

            popupNode.remove();

            editor.on("cursorActivity", function () {

                var cursor = editor.getCursor();
                //console.log(cursor);

                popupNode.remove();

                /*if (cursor.line == 3 && cursor.ch >= 0 && cursor.ch <= 13) {
                    var text = document.createTextNode("We can say a bunch of stuff about why this is highlighted right here.");
                    popupNode.innerHTML = '';
                    popupNode.appendChild(text);
                    editor.addWidget({ line: 4, ch: 9 }, popupNode, true);
                } else {
                    popupNode.remove();
                }*/

                for(var i=0; i<result['docstring_results'][1].length; i++){

                    if( result['docstring_results'][1][i][0] == filename ){
                        for(var j=0; j<result['docstring_results'][1][i][1].length; j++){

                            if( result['docstring_results'][1][i][1][j].result.length > 0 ){                        

                                if (cursor.line == result['docstring_results'][1][i][1][j].result[0][1] ) {
                                    var text = document.createTextNode(result['docstring_results'][1][i][1][j].result[0][0]);
                                    popupNode.innerHTML = '';
                                    popupNode.appendChild(text);
                                    editor.addWidget({ line: cursor.line, ch: 9 }, popupNode, true);
                                }
                            }
                        }
                    }
                }


            });


            setTimeout(function () {
                editor.refresh();
            }, 1);

            $('#docModal').modal('show');
        }
    });

}



function showCqEditor(docfilename, difftext) {

    console.log("CQ TEST");
    console.log(difftext);

    filename = docfilename;

    $('#cqhelpertitle').html(filename);

    //$('#dochelper').empty();

    $.ajax({
        url: '/dashboard/getfile/', type: 'POST', data: { 'pr': pr, 'filename': filename }, success: function (result) {
            console.log("get file contents");
            console.log(result);

            cqeditor.setValue(result['filecontents']);

            //editor.markText({ line: 3, ch: 0 }, { line: 3, ch: 13 }, { className: "styled-background" });
            //editor.markText({ line: 6, ch: 12 }, { line: 6, ch: 22 }, { className: "styled-background" });
            //editor.markText({ line: 4, ch: 2 }, { line: 4, ch: 6 }, { className: "styled-background" });

            for(var i=0; i<result['linter_results'].length; i++){
                cqeditor.markText({ line: result['linter_results'][i].line-1, ch: result['linter_results'][i].column }, { line: result['linter_results'][i].line-1, ch: 100 }, { className: "styled-background" });
            }

            popupNode.remove();

            cqeditor.on("cursorActivity", function () {

                var cursor = cqeditor.getCursor();

                popupNode.remove();

                for(var i=0; i<result['linter_results'].length; i++){

                    if (cursor.line == result['linter_results'][i].line-1 && cursor.ch >= result['linter_results'][i].column) {
                        var text = document.createTextNode(result['linter_results'][i].type +": "+ result['linter_results'][i].message);
                        popupNode.innerHTML = '';
                        popupNode.appendChild(text);
                        cqeditor.addWidget({ line: cursor.line, ch: 9 }, popupNode, true);
                    }
                }
            });


            setTimeout(function () {
                cqeditor.refresh();
            }, 1);

            $('#codeQualityModal').modal('show');
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


function cqPatchFile() {

    console.log(cqeditor.getValue());


    $.ajax({
        url: '/dashboard/createpatch/', type: 'POST', data: { 'pr': pr, 'filename': filename, 'filecontents': cqeditor.getValue() }, success: function (result) {

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
        xhr.setRequestHeader("X-CSRFToken", csrf_token);
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

        var cqtable = $("#cqdiffcommittable > tbody");
        cqtable.empty();

        var atable = $("#adiffcommittable > tbody");
        atable.empty();

        for (var i = 0; i < result['diffcommits'].length; i++) {
            var commits = "";
            var diffs = "";
            var doccommits = "";
            var docbuttons = "";
            var cqbuttons = "";
            var alinks = "";
            var issues = 0;

            for (var j = 0; j < result['diffcommits'][i]['commits'].length; j++) {

                var diff = result['diffcommits'][i]['commits'][j]['diff'];
                var diffadds = (diff.charAt(0) == '+' ? 1 : 0);
                var diffsubs = (diff.charAt(0) == '-' ? 1 : 0);

                diffadds += (diff.match(/\n\+/g) || []).length;
                diffsubs += (diff.match(/\n\-/g) || []).length;

                commits += "<a target='_blank' href='" + result['source_url'] + "/commit/" + result['diffcommits'][i]['commits'][j]['commit'] + "'>" + result['diffcommits'][i]['commits'][j]['commit'].substring(0, 7) + "</a><br/>";


                diff = diff.replace(/&/g, '&amp;').replaceAll('\"', '&quot;').replaceAll('\'', '&lsquo;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                diffs += "<span data-bs-toggle='popover' data-bs-trigger='hover' data-bs-html='true' data-bs-placement='left' data-bs-content='<pre>" + diff.substring(0, Math.min(diff.length, 1000)) + "</pre>'>" + diffadds + "&nbsp;adds,&nbsp;" + diffsubs + "&nbsp;subs</span><br/>";

                //see if we should add commit to doc file table
                for (var k = 0; k < result['prcommits'].length; k++) {
                    if (result['diffcommits'][i]['commits'][j]['commit'] == result['prcommits'][k]['hash']) {
                        doccommits += "<a target='_blank' href='" + result['source_url'] + "/commit/" + result['diffcommits'][i]['commits'][j]['commit'] + "'>" + result['diffcommits'][i]['commits'][j]['commit'].substring(0, 7) + "</a><br/>";
                        docbuttons += "<button class='btn btn-sm btn-primary' onclick='showDocEditor(\"" + result['diffcommits'][i]['filename'] + "\",\"" + "DIFF STUFF TO GO HERE" + "\");'>View File in Editor</button><br/>";
                        cqbuttons += "<button class='btn btn-sm btn-primary' onclick='showCqEditor(\"" + result['diffcommits'][i]['filename'] + "\",\"" + "DIFF STUFF TO GO HERE" + "\");'>View File in Editor</button><br/>";
                        alinks += "<a class='btn btn-sm btn-primary' href='/dashboard/archeology/" + pr + "?filename=" +result['diffcommits'][i]['filename']+ "'>View Archeology</a><br/>";

                    }
                }

            }

            //see if there are docstring issues
            for (var k = 0; k < result['docstring_results'][1].length; k++) {
                if (result['diffcommits'][i]['filename'] == result['docstring_results'][1][k][0]) {
                    for (var m = 0; m < result['docstring_results'][1][k][1].length; m++) {
                        if( result['docstring_results'][1][k][1][m].result.length > 0 ){
                            issues++;
                            //issues = result['docstring_results'][1][k][1].length;
                        }
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
                    "<a href='/dashboard/pr/"+pr+"'>"+result['diffcommits'][i]['filename'] +"</a>"+
                "</td><td>" +
                    issues +
                "</td><td>" +
                    docbuttons +
                "</td></tr>");

            cqtable.append("<tr><td>"+
                    "<a href='/dashboard/pr/"+pr+"'>"+result['diffcommits'][i]['filename'] +"</a>"+
                "</td><td>"+
                    "N/A"+
                "</td><td>"+
                    cqbuttons+
                "</td></tr>");

            atable.append("<tr><td>"+
                    result['diffcommits'][i]['filename']+
                    "</td><td>"+
                            doccommits+
                    "</td><td>"+
                            alinks+
                    "</td></tr>");

        }

        $('.popover-dismiss').popover({ trigger: 'focus' });

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
