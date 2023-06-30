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
var prauthor = $("#prauthor").val();
var project = $("#project").val();
var branch = $("#branch").val();
console.log("The PR id...");
console.log($("#pr"));
console.log(pr);
console.log(prauthor);
var filename = "";
var previousLines = 0;
var ignoreLineChanges = true;
var docstring_results = [];

var popupNode = document.createElement("div");
popupNode.style.border = '2px solid grey'
popupNode.style.padding = '5px'
popupNode.style.background = 'white'
popupNode.style.color = 'black';
popupNode.style.zIndex = '9999';

let csrf_token = document.querySelector('[name=csrfmiddlewaretoken]').value;

$.ajaxSetup({
    beforeSend: function (xhr, settings) {
        xhr.setRequestHeader("X-CSRFToken", csrf_token);
    }
});

console.log("PR");
console.log(pr);

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

var testeditor = CodeMirror.fromTextArea(document.getElementById("testhelper"), {
    lineNumbers: true,
    mode: "text/x-python", //"text/x-c++src", //"text/html",
    matchBrackets: true,
    spellcheck: true,
    autocorrect: true,
    styleSelectedText: true
});

function showDocEditor(docfilename, difftext) {

    console.log("------- TEST --------");
    console.log(docfilename);
    console.log(pr);
    console.log(csrf_token);

    filename = docfilename;

    $('#dochelpertitle').html(filename);
    previousLines = 0;
    ignoreLineChanges = true;

    //$('#dochelper').empty();

    $.ajax({
        url: '/dashboard/logevent/', type: 'POST', data: { 'pr': pr, 'comments': 'Documentation editor opened for: '+filename }, success: function (result) {
            console.log("success ajax");
            console.log(result);
        }
    });

    $.ajax({
        url: '/dashboard/getfile/', type: 'POST', data: { 'pr': pr, 'filename': filename }, success: function (result) {
            console.log("get file contents");
            console.log(result);

            if( filename.indexOf(".h") >= 0 || filename.indexOf(".c") ){
                editor.setOption("mode", "text/x-c++src");
            }else if( filename.indexOf(".py") >= 0 ){
                editor.setOption("mode", "text/x-python");
            }else if( filename.indexOf(".F90") >= 0 || filename.indexOf(".dox") >= 0 ){
                editor.setOption("mode", "text/x-fortran");
            }else{
                editor.setOption("mode", "text/html");
            }

            editor.setValue(result['filecontents']);

            previousLines = editor.lineCount();
            ignoreLineChanges = false;

            //editor.markText({ line: 3, ch: 0 }, { line: 3, ch: 13 }, { className: "styled-background" });
            //editor.markText({ line: 6, ch: 12 }, { line: 6, ch: 22 }, { className: "styled-background" });
            //editor.markText({ line: 4, ch: 2 }, { line: 4, ch: 6 }, { className: "styled-background" });

            //for(var i=0; i<result['linter_results'].length; i++){
            //    editor.markText({ line: result['linter_results'][i].line-1, ch: result['linter_results'][i].column }, { line: result['linter_results'][i].line-1, ch: 100 }, { className: "styled-background" });
            //}
/*
            for(var i=0; i<docstring_results[1].length; i++){

                if( docstring_results[1][i][0] == filename ){
                    for(var j=0; j<docstring_results[1][i][1].length; j++){

                        if( docstring_results[1][i][1][j].result.length > 0 ){ 

                            for(var k=0; k<docstring_results[1][i][1][j].result.length; k++){ 
                                
                                if( docstring_results[1][i][1][j].result[k][0].indexOf("No docstring") >= 0 ){
                                    docstring_results[1][i][1][j].result[k][1] -= 1;
                                }
                                console.log("MARK LINE: " + docstring_results[1][i][1][j].result[k][1] ); 
                                editor.markText({ line: docstring_results[1][i][1][j].result[k][1], ch: 0 }, { line: docstring_results[1][i][1][j].result[k][1], ch: 100 }, { className: "styled-background" });
                            }
                        }
                    }
                }
            }
*/
            var file_doc_results = docstring_results[filename];

            if( filename.indexOf(".F90") >= 0 || filename.indexOf(".dox") >= 0 ){
                if( file_doc_results['documentation_lib']['file_status'].indexOf("checkable") == 0 ){
                    for(var i=0; i<file_doc_results['documentation_lib']['problem_fields'].length; i++){
                        editor.markText({ line: file_doc_results['documentation_lib']['problem_fields'][i][2], ch: 0 }, { line: file_doc_results['documentation_lib']['problem_fields'][i][2], ch: 100 }, { className: "styled-background" });
                    }
                    //for(var i=0; i<file_doc_results['documentation_lib']['missing_fields'].length; i++){
                    if( file_doc_results['documentation_lib']['missing_fields'].length > 0){
                        editor.markText({ line: 0, ch: 0 }, { line: 0, ch: 100 }, { className: "styled-background" });
                    }
                    //for(var i=0; i<file_doc_results['documentation_lib']['missing_file_fields'].length; i++){
                    if( file_doc_results['documentation_lib']['missing_file_fields'].length > 0){
                        editor.markText({ line: 0, ch: 0 }, { line: 0, ch: 100 }, { className: "styled-background" });
                    }
                    for(var i=0; i<file_doc_results['documentation_lib']['missing_subroutine_fields'].length; i++){
                        editor.markText({ line: file_doc_results['documentation_lib']['missing_subroutine_fields'][i][0], ch: 0 }, { line: file_doc_results['documentation_lib']['missing_subroutine_fields'][i][0], ch: 100 }, { className: "styled-background" });
                    }
                }
            }else if( file_doc_results['documentation']['check_status'] && !file_doc_results['documentation']['documentation.doc_status'] ){
                //docissues = file_doc_results['documentation']['problem_lines'].length;
                for(var i=0; i<file_doc_results['documentation']['problem_lines'].length; i++){
                    // Problem line format: ['message', linenumber]
                    //For some reason, the line is off by one 
                    file_doc_results['documentation']['problem_lines'][i][1] -= 1;
                    editor.markText({ line: file_doc_results['documentation']['problem_lines'][i][1], ch: 0 }, { line: file_doc_results['documentation']['problem_lines'][i][1], ch: 100 }, { className: "styled-background" });
                }
            }

            /* JUST FOR DEMO */
            //editor.markText({ line: 6, ch: 0 }, { line: 7, ch: 100 }, { className: "styled-background" });
            /* */

            popupNode.remove();

            editor.on("cursorActivity", function () {

                var cursor = editor.getCursor();
                var lines = editor.lineCount();
                
                console.log(previousLines + " now -> "+lines);
                console.log("ignore: "+ignoreLineChanges);

                if( !ignoreLineChanges && lines > previousLines ){

                    //Bump the line numbers by 1 if after linenumber (this is currenlty only looking at first item in results)
/*                    
                    for(var i=0; i<docstring_results[1].length; i++){
                        if( docstring_results[1][i][0] == filename ){
                            for(var j=0; j<docstring_results[1][i][1].length; j++){
                                if( docstring_results[1][i][1][j].result.length > 0 ){     
                                    if( cursor.line <= docstring_results[1][i][1][j].result[0][1] ){
                                        docstring_results[1][i][1][j].result[0][1] += 1;
                                    }
                                }
                            }
                        }
                    }
*/  
                    var file_doc_results = docstring_results[filename];
                    if( filename.indexOf(".F90") >= 0 || filename.indexOf(".docx") >= 0){
                        if( file_doc_results['documentation_lib']['file_status'].indexOf("checkable") == 0 ){
                            for(var i=0; i<file_doc_results['documentation_lib']['problem_fields'].length; i++){
                                // Problem line format: ['message', 'line', linenumber]
                                 if( cursor.line <= file_doc_results['documentation_lib']['problem_fields'][i][2] ){
                                    file_doc_results['documentation_lib']['problem_fields'][i][2] += 1;
                                }
                            } 
                        }
                    }else{
                        for(var i=0; i<file_doc_results['documentation']['problem_lines'].length; i++){
                            // Problem line format: ['message', linenumber]
                             if( cursor.line <= file_doc_results['documentation']['problem_lines'][i][1] ){
                                file_doc_results['documentation']['problem_lines'][i][1] += 1;
                            }
                        }    
                    }                
                    previousLines = lines;
                }

                popupNode.remove();

                /*if (cursor.line == 3 && cursor.ch >= 0 && cursor.ch <= 13) {
                    var text = document.createTextNode("We can say a bunch of stuff about why this is highlighted right here.");
                    popupNode.innerHTML = '';
                    popupNode.appendChild(text);
                    editor.addWidget({ line: 4, ch: 9 }, popupNode, true);
                } else {
                    popupNode.remove();
                }*/
/*
                for(var i=0; i<docstring_results[1].length; i++){

                    if( docstring_results[1][i][0] == filename ){
                        for(var j=0; j<docstring_results[1][i][1].length; j++){

                            if( docstring_results[1][i][1][j].result.length > 0 ){                        

                                if (cursor.line == docstring_results[1][i][1][j].result[0][1] ) {
                                    
                                    popupNode.innerHTML = '';
                                    for(var k=0; k<docstring_results[1][i][1][j].result.length; k++){
                                        var text = document.createTextNode(docstring_results[1][i][1][j].result[k][0]);
                                        popupNode.appendChild(text);
                                        if( k < docstring_results[1][i][1][j].result.length-1 ){
                                            var br = document.createElement('br');
                                            popupNode.appendChild(br);
                                        }
                                    }

                                    

                                    if( docstring_results[1][i][1][j].result[0][0].indexOf("No docstring") >= 0 ){
                                        var button = document.createElement('button');
                                        button.setAttribute('onclick', 'insertTemplate('+(cursor.line)+', \'  \"\"\"\\n  Template will go here.\\n  \"\"\"\')');
                                        button.classList.add('btn');
                                        button.classList.add('btn-sm');
                                        button.classList.add('btn-primary');
                                        button.style['margin-left'] = "10px"
                                        button.innerHTML = 'Insert docstring template'
                                        popupNode.appendChild(button);
                                    }
                                    editor.addWidget({ line: cursor.line, ch: 9 }, popupNode, true);
                                }
                            }
                        }
                    }
                }
*/
                var file_doc_results = docstring_results[filename];
                if( filename.indexOf(".F90") >= 0 || filename.indexOf(".F90-mc") >= 0 || filename.indexOf(".dox") >= 0 ){
                    for(var i=0; i<file_doc_results['documentation_lib']['problem_fields'].length; i++){
                        // Problem line format: ['message', linenumber]
                        if (cursor.line == file_doc_results['documentation_lib']['problem_fields'][i][2] ) {
                            
                            popupNode.innerHTML = '';
                            var text = document.createTextNode(file_doc_results['documentation_lib']['problem_fields'][i][0]);
                            popupNode.appendChild(text);
                  
                            if( file_doc_results['documentation_lib']['problem_fields'][i][0].indexOf("No docstring") >= 0 ){
                                var button = document.createElement('button');
                                button.setAttribute('onclick', 'insertTemplate('+(cursor.line)+', \'  \"\"\"\\n  Template will go here.\\n  \"\"\"\')');
                                button.classList.add('btn');
                                button.classList.add('btn-sm');
                                button.classList.add('btn-primary');
                                button.style['margin-left'] = "10px"
                                button.innerHTML = 'Insert docstring template'
                                popupNode.appendChild(button);
                            }
                            editor.addWidget({ line: cursor.line, ch: 9 }, popupNode, true);
                        }
                    }
                    //for(var i=0; i<file_doc_results['documentation_lib']['missing_fields'].length; i++){
                    if( file_doc_results['documentation_lib']['missing_fields'].length > 0){
                        // Problem line format: ['message', linenumber]
                        if (cursor.line == 0 ) {
                            
                            popupNode.innerHTML = '';
                            var text = document.createTextNode("Missing fields: "+file_doc_results['documentation_lib']['missing_fields']);
                            popupNode.appendChild(text);
                  
                            editor.addWidget({ line: cursor.line, ch: 9 }, popupNode, true);
                        }
                    }  
                    //for(var i=0; i<file_doc_results['documentation_lib']['missing_file_fields'].length; i++){
                    if( file_doc_results['documentation_lib']['missing_file_fields'].length > 0){
                        // Problem line format: ['message', linenumber]
                        if (cursor.line == 0 ) {
                            
                            popupNode.innerHTML = '';
                            var text = document.createTextNode("Missing file fields: "+file_doc_results['documentation_lib']['missing_file_fields']);
                            popupNode.appendChild(text);
                  
                            editor.addWidget({ line: cursor.line, ch: 9 }, popupNode, true);
                        }
                    }  

                    subroutine_text = []
                    for(var i=0; i<file_doc_results['documentation_lib']['missing_subroutine_fields'].length; i++){
                        // Problem line format: ['message', linenumber]
                        if (cursor.line ==  file_doc_results['documentation_lib']['missing_subroutine_fields'][i][0] ) {
                            
                            subroutine_text.push(file_doc_results['documentation_lib']['missing_subroutine_fields'][i][1]);
                        }
                    }  
                    if( subroutine_text.length > 0 ){
                        popupNode.innerHTML = '';
                        var text = document.createTextNode("Missing fields: "+subroutine_text);
                        popupNode.appendChild(text);
                        editor.addWidget({ line: cursor.line, ch: 9 }, popupNode, true);
                    }
                }else{
                    for(var i=0; i<file_doc_results['documentation']['problem_lines'].length; i++){
                        // Problem line format: ['message', linenumber]
                        if (cursor.line == file_doc_results['documentation']['problem_lines'][i][1] ) {
                            
                            popupNode.innerHTML = '';
                            var text = document.createTextNode(file_doc_results['documentation']['problem_lines'][i][0]);
                            popupNode.appendChild(text);
                  
                            if( file_doc_results['documentation']['problem_lines'][i][0].indexOf("No docstring") >= 0 ){
                                var button = document.createElement('button');
                                button.setAttribute('onclick', 'insertTemplate('+(cursor.line)+', \'  \"\"\"\\n  Template will go here.\\n  \"\"\"\')');
                                button.classList.add('btn');
                                button.classList.add('btn-sm');
                                button.classList.add('btn-primary');
                                button.style['margin-left'] = "10px"
                                button.innerHTML = 'Insert docstring template'
                                popupNode.appendChild(button);
                            }
                            editor.addWidget({ line: cursor.line, ch: 9 }, popupNode, true);
                        }
                    } 
                }

                /* JUST FOR DEMO */
                //var text = document.createTextNode("Test cases no longer valid.");
                //popupNode.innerHTML = '';
                //popupNode.appendChild(text);
                //editor.addWidget({ line: cursor.line, ch: 9 }, popupNode, true);
                /* */

            });


            setTimeout(function () {
                editor.refresh();
            }, 1);

            $('#docModal').modal('show');
        }
    });

}


function insertTemplate(linenumber, text){

    console.log("get template");
    var cursor = editor.getCursor();
    console.log( editor.getLine(cursor.line) );

    $.ajax({
        url: '/dashboard/getdoctemplate/', type: 'POST', data: { 'pr': pr, 'filename': filename, 'signature': editor.getLine(cursor.line) }, success: function (result) {
            console.log("got template");
            console.log(result);

            result.template = result.template.replaceAll('\\n','\n')
            console.log(result);

            editor.replaceRange('\n'+result.template, CodeMirror.Pos(linenumber));
            popupNode.remove();

            var lines = (result.template.match(/\n/g) || []).length + 1;
            console.log("Lines: "+lines);

            console.log ("Insert at template at: "+linenumber);

            //Bump the line numbers by 3 if after linenumber (this is currenlty only looking at first item in results)
            for(var i=0; i<docstring_results[1].length; i++){
                if( docstring_results[1][i][0] == filename ){
                    for(var j=0; j<docstring_results[1][i][1].length; j++){
                        if( docstring_results[1][i][1][j].result.length > 0 ){     
                            console.log("checking... "+docstring_results[1][i][1][j].result[0][1]);                   
                            if( linenumber < docstring_results[1][i][1][j].result[0][1]-1 ){
                                docstring_results[1][i][1][j].result[0][1] += lines;
                            }
                        }
                    }
                }
            }
            previousLines += lines;

        }
    });
    
}


function showDoxygenEditor(docfilename, newFileContent, oldDocContent) {

    console.log("------- TEST --------");
    console.log(docfilename);
    console.log(pr);
    console.log(csrf_token);

    filename = docfilename;

    $('#dochelpertitle').html(filename);
    previousLines = 0;
    ignoreLineChanges = true;

    $.ajax({
        url: '/dashboard/getfile/', type: 'POST', data: { 'pr': pr, 'filename': filename }, success: function (result) {
            console.log("get file contents");
            console.log(result);

            if( filename.indexOf(".h") >= 0 || filename.indexOf(".c") ){
                editor.setOption("mode", "text/x-c++src");
            }else if( filename.indexOf(".py") >= 0 ){
                editor.setOption("mode", "text/x-python");
            }else if( filename.indexOf(".F90") >= 0 ){
                editor.setOption("mode", "text/x-fortran");
            }else{
                editor.setOption("mode", "text/html");
            }

            editor.setValue(result['filecontents']);

            previousLines = editor.lineCount();
            ignoreLineChanges = false;

            //editor.markText({ line: 3, ch: 0 }, { line: 3, ch: 13 }, { className: "styled-background" });
            //editor.markText({ line: 6, ch: 12 }, { line: 6, ch: 22 }, { className: "styled-background" });
            //editor.markText({ line: 4, ch: 2 }, { line: 4, ch: 6 }, { className: "styled-background" });

            //for(var i=0; i<result['linter_results'].length; i++){
            //    editor.markText({ line: result['linter_results'][i].line-1, ch: result['linter_results'][i].column }, { line: result['linter_results'][i].line-1, ch: 100 }, { className: "styled-background" });
            //}

            for(var i=0; i<docstring_results[1].length; i++){

                if( docstring_results[1][i][0] == filename ){
                    for(var j=0; j<docstring_results[1][i][1].length; j++){

                        if( docstring_results[1][i][1][j].result.length > 0 ){ 

                            for(var k=0; k<docstring_results[1][i][1][j].result.length; k++){ 
                                
                                if( docstring_results[1][i][1][j].result[k][0].indexOf("No docstring") >= 0 ){
                                    docstring_results[1][i][1][j].result[k][1] -= 1;
                                }
                                console.log("MARK LINE: " + docstring_results[1][i][1][j].result[k][1] ); 
                                editor.markText({ line: docstring_results[1][i][1][j].result[k][1], ch: 0 }, { line: docstring_results[1][i][1][j].result[k][1], ch: 100 }, { className: "styled-background" });
                            }
                        }
                    }
                }
            }

            /* JUST FOR DEMO */
            //editor.markText({ line: 6, ch: 0 }, { line: 7, ch: 100 }, { className: "styled-background" });
            /* */

            popupNode.remove();

            editor.on("cursorActivity", function () {

                var cursor = editor.getCursor();
                var lines = editor.lineCount();
                
                console.log(previousLines + " now -> "+lines);
                console.log("ignore: "+ignoreLineChanges);

                if( !ignoreLineChanges && lines > previousLines ){

                    //Bump the line numbers by 1 if after linenumber (this is currenlty only looking at first item in results)
                    for(var i=0; i<docstring_results[1].length; i++){
                        if( docstring_results[1][i][0] == filename ){
                            for(var j=0; j<docstring_results[1][i][1].length; j++){
                                if( docstring_results[1][i][1][j].result.length > 0 ){     
                                    if( cursor.line <= docstring_results[1][i][1][j].result[0][1] ){
                                        docstring_results[1][i][1][j].result[0][1] += 1;
                                    }
                                }
                            }
                        }
                    }
                    previousLines = lines;
                }

                popupNode.remove();

                /*if (cursor.line == 3 && cursor.ch >= 0 && cursor.ch <= 13) {
                    var text = document.createTextNode("We can say a bunch of stuff about why this is highlighted right here.");
                    popupNode.innerHTML = '';
                    popupNode.appendChild(text);
                    editor.addWidget({ line: 4, ch: 9 }, popupNode, true);
                } else {
                    popupNode.remove();
                }*/

                for(var i=0; i<docstring_results[1].length; i++){

                    if( docstring_results[1][i][0] == filename ){
                        for(var j=0; j<docstring_results[1][i][1].length; j++){

                            if( docstring_results[1][i][1][j].result.length > 0 ){                        

                                if (cursor.line == docstring_results[1][i][1][j].result[0][1] ) {
                                    
                                    popupNode.innerHTML = '';
                                    for(var k=0; k<docstring_results[1][i][1][j].result.length; k++){
                                        var text = document.createTextNode(docstring_results[1][i][1][j].result[k][0]);
                                        popupNode.appendChild(text);
                                        if( k < docstring_results[1][i][1][j].result.length-1 ){
                                            var br = document.createElement('br');
                                            popupNode.appendChild(br);
                                        }
                                    }

                                    

                                    if( docstring_results[1][i][1][j].result[0][0].indexOf("No docstring") >= 0 ){
                                        var button = document.createElement('button');
                                        button.setAttribute('onclick', 'insertTemplate('+(cursor.line)+', \'  \"\"\"\\n  Template will go here.\\n  \"\"\"\')');
                                        button.classList.add('btn');
                                        button.classList.add('btn-sm');
                                        button.classList.add('btn-primary');
                                        button.style['margin-left'] = "10px"
                                        button.innerHTML = 'Insert docstring template'
                                        popupNode.appendChild(button);
                                    }
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


function sendInvite(email, filenames){

    console.log("Send Invite");
    console.log(email);
    console.log(filenames);

    $.ajax({
        url: '/dashboard/sendinvite/', type: 'POST', data: { 'pr': pr, 'email': email, 'filenames': filenames}, success: function (result) {
            console.log("got invite response");
            console.log(result);

            alert('Invite sent to developer.');
        }
    });

    return true;
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

            if( filename.indexOf(".h") >= 0 || filename.indexOf(".c") ){
                cqeditor.setOption("mode", "text/x-c++src");
            }else if( filename.indexOf(".py") >= 0 ){
                cqeditor.setOption("mode", "text/x-python");
            }else if( filename.indexOf(".F90") >= 0 ){
                cqeditor.setOption("mode", "text/x-fortran");
            }else{
                cqeditor.setOption("mode", "text/html");
            }

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


function showTestEditor(docfilename, difftext) {

    console.log("TEST");
    console.log(difftext);

    filename = docfilename;

    $('#testhelpertitle').html(filename);


    $.ajax({
        url: '/dashboard/getfile/', type: 'POST', data: { 'pr': pr, 'filename': filename }, success: function (result) {
            console.log("get file contents");
            console.log(result);
            console.log(filename);

            if( filename.indexOf(".h") >= 0 || filename.indexOf(".c") ){
                testeditor.setOption("mode", "text/x-c++src");
            }else if( filename.indexOf(".py") >= 0 ){
                testeditor.setOption("mode", "text/x-python");
            }else if( filename.indexOf(".F90") >= 0 ){
                testeditor.setOption("mode", "text/x-fortran");
            }else{
                testeditor.setOption("mode", "text/html");
            }

            testeditor.setValue(result['filecontents']);

            //editor.markText({ line: 3, ch: 0 }, { line: 3, ch: 13 }, { className: "styled-background" });
            //editor.markText({ line: 6, ch: 12 }, { line: 6, ch: 22 }, { className: "styled-background" });
            //editor.markText({ line: 4, ch: 2 }, { line: 4, ch: 6 }, { className: "styled-background" });

            for(var i=0; i<docstring_results[1].length; i++){

                for(var j=0; j<docstring_results[1][i][1].length; j++){

                    for(var k=0; k<docstring_results[1][i][1][j].test_info.length; k++){ 

                        console.log(docstring_results[1][i][1][j].test_info[k][0]+'/'+docstring_results[1][i][1][j].test_info[k][1]);

                        if( docstring_results[1][i][1][j].test_info[k][0]+'/'+docstring_results[1][i][1][j].test_info[k][1] == filename ){

                            console.log("TEST MARK LINE: " + docstring_results[1][i][1][j].test_info[k][2] );                      
                            testeditor.markText({ line: docstring_results[1][i][1][j].test_info[k][2], ch: 0 }, { line: docstring_results[1][i][1][j].test_info[k][2], ch: 100 }, { className: "styled-background" });
                        }
                    }   
                }
            }


            popupNode.remove();

            testeditor.on("cursorActivity", function () {

                var cursor = testeditor.getCursor();

                popupNode.remove();

                for(var i=0; i<docstring_results[1].length; i++){

                    for(var j=0; j<docstring_results[1][i][1].length; j++){

                        for(var k=0; k<docstring_results[1][i][1][j].test_info.length; k++){ 

                            if( docstring_results[1][i][1][j].test_info[k][0]+'/'+docstring_results[1][i][1][j].test_info[k][1] == filename ){

                                if( cursor.line == docstring_results[1][i][1][j].test_info[k][2] ){
                                    var text = document.createTextNode("Please check this test for correctness.");
                                    popupNode.innerHTML = '';
                                    popupNode.appendChild(text);
                                    testeditor.addWidget({ line: cursor.line, ch: 9 }, popupNode, true);
                                }
                            }
                        }   
                    }
                }
            });


            setTimeout(function () {
                testeditor.refresh();
            }, 1);

            $('#testModal').modal('show');
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



$.ajax({
    url: '/dashboard/diffcommitdata/', type: 'POST', data: { 'pr': pr }, success: function (result) {
        console.log("success diff commits");
        console.log(result);

        var table = $("#diffcommittable > tbody");
        table.empty();

        var cqtable = $("#cqdiffcommittable > tbody");
        cqtable.empty();

        var atable = $("#adiffcommittable > tbody");
        atable.empty();

        for (var i = 0; i < result['diffcommits'].length; i++) {
            var commits = "";
            var diffs = "";
            var doccommits = "";
            var cqbuttons = "";
            var alinks = "";

            var cqissues = -1;

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
                        //docbuttons += "<button class='btn btn-sm btn-primary' onclick='showDocEditor(\"" + result['diffcommits'][i]['filename'] + "\",\"" + "DIFF STUFF TO GO HERE" + "\");'>View File in Editor</button><br/>";
                        //cqbuttons += "<button class='btn btn-sm btn-primary' onclick='showCqEditor(\"" + result['diffcommits'][i]['filename'] + "\",\"" + "DIFF STUFF TO GO HERE" + "\");'>View File in Editor</button><br/>";
                        alinks += "<a class='btn btn-sm btn-primary' href='/dashboard/archeology/" + pr + "?filename=" +result['diffcommits'][i]['filename']+ "'>View Archeology</a><br/>";
                    }
                }

            }

            cqbuttons += "<button class='btn btn-sm btn-primary' onclick='showCqEditor(\"" + result['diffcommits'][i]['filename'] + "\",\"" + "DIFF STUFF TO GO HERE" + "\");'>View File in Editor</button><br/>";
 
            for (var k = 0; k < result['linter_results'].length; k++) {
                if (result['diffcommits'][i]['filename'] == result['linter_results'][k]['filename']) {
                    //for (var m = 0; m < result['docstring_results'][1][k][1].length; m++) {
                        //if( result['docstring_results'][1][k][1][m].result.length > 0 ){
                            cqissues = result['linter_results'][k]['results'].length;
                        //}
                    //}
                }
            }



            table.append("<tr><td>" +
                result['diffcommits'][i]['filename'] +
                "</td><td>" +
                commits +
                "</td><td>" +
                diffs +
                "</td></tr>");


            if( project == 30 || project == 26 || project == 35 || project == 32 ){
                cqtable.append("<tr><td>"+
                        "<span>"+result['diffcommits'][i]['filename'] +"</span>"+
                        "<br/><a class='btn btn-xs btn-secondary' target='_blank' href='/dashboard/filex/"+project+"?filename="+result['diffcommits'][i]['filename']+"&branch="+branch+"'>View in File Explorer</a>"+
                    "</td><td>"+
                        (cqissues < 0 ? '-' : cqissues) +
                    "</td><td>"+
                        (cqissues > 0 ? cqbuttons : '') +
                    "</td></tr>");
            }

            atable.append("<tr><td>"+
                    result['diffcommits'][i]['filename']+
                    "</td><td>"+
                            doccommits+
                    "</td><td>"+
                            alinks+
                    "</td></tr>");

            if( cqissues > 0 )
                $("#cqwarning").show();

        }


        if( !(project == 30 || project == 26 || project == 35 || project == 32 ) ){
            cqtable.append("<tr><td colspan='3'>"+
                    "<i>This project is not supported yet.</i>"+
                "</td></tr>");
        }


        docstring_results = result['docstring_results'];
        var doctable = $("#docdiffcommittable > tbody");
        doctable.empty();

        for (var i = 0; i < result['diffcommits'].length; i++) {
            var filename = result['diffcommits'][i]['filename'];


            var file_doc_results = result['docstring_results'][filename];
            console.log(file_doc_results);

            var docbuttons = "";
            var docissues = -1;
            var docstatus = "-";
            docbuttons += "<button class='btn btn-sm btn-primary' onclick='showDocEditor(\"" + filename + "\",\"" + "DIFF STUFF TO GO HERE" + "\");'>View File in Editor</button><br/>";
 
            //Compute number of issues
            if( filename.indexOf(".F90") >= 0 || filename.indexOf(".dox") >= 0 ){
                if( file_doc_results['documentation_lib']['file_status'] && file_doc_results['documentation_lib']['file_status'].indexOf("checkable") == 0 ){
                    docissues = 0;
                    try{
                        docissues = file_doc_results['documentation_lib']['problem_fields'].length + file_doc_results['documentation_lib']['missing_fields'].length + file_doc_results['documentation_lib']['missing_file_fields'].length + file_doc_results['documentation_lib']['missing_subroutine_fields'].length;
                    }catch(error){
                        console.log(error);
                    }
                    if( file_doc_results['documentation_lib']['file_status'].indexOf("checkable but no documentation") == 0 ){
                        docissues = '-';
                    }
                }
            }else if( file_doc_results['documentation']['check_status'] && !file_doc_results['documentation']['doc_status'] ){
                docissues = 0;
                try{
                    docissues = file_doc_results['documentation']['problem_lines'].length;
                }catch(error){}
            }

            if( file_doc_results['documentation_lib']['file_status'] )
                docstatus = file_doc_results['documentation_lib']['file_status']; //.replaceAll('/','/<br/>');

            if( docstatus.indexOf("uncheckable") >= 0  ){
                if( docstatus.indexOf("no documentation") >= 0 ){
                    doctable.append("<tr><td>" +
                        "<span>"+filename +"</span>"+
                        "<br/><a class='btn btn-xs btn-secondary' target='_blank' href='/dashboard/filex/"+project+"?filename="+filename+"&branch="+branch+"'>View in File Explorer</a>"+
                        "</td><td>" +
                            docstatus +
                        "</td><td>" +
                            '-' +
                        "</td><td>" +
                            "<a class='btn btn-sm btn-primary' target='_blank' href='#''>View Doc Template</a><br/>" +
                        "</td></tr>");
                }else{
                    doctable.append("<tr><td>" +
                        "<span>"+filename +"</span>"+
                        "<br/><a class='btn btn-xs btn-secondary' target='_blank' href='/dashboard/filex/"+project+"?filename="+filename+"&branch="+branch+"'>View in File Explorer</a>"+
                        "</td><td colspan='3'>" +
                            docstatus +
                        "</td></tr>");
                }
            }else{

                    doctable.append("<tr><td>" +
                        "<span>"+filename +"</span>"+
                        "<br/><a class='btn btn-xs btn-secondary' target='_blank' href='/dashboard/filex/"+project+"?filename="+filename+"&branch="+branch+"'>View in File Explorer</a>"+
                        "</td><td>" +
                            docstatus +
                        "</td><td>" +
                            (docissues < 0 ? '-' : docissues) +
                        "</td><td>" +
                            docbuttons +
                        "</td></tr>");
                
            }

            if( docissues > 0 )
                $("#docwarning").show();
        }


/*
        for (var k = 0; k < result['docstring_results'][1].length; k++) {
            var docbuttons = "";
            var docissues = -1;
            docbuttons += "<button class='btn btn-sm btn-primary' onclick='showDocEditor(\"" + result['docstring_results'][1][k][0] + "\",\"" + "DIFF STUFF TO GO HERE" + "\");'>View File in Editor</button><br/>";
 

            //see if there are docstring issues
            //for (var k = 0; k < result['docstring_results'][1].length; k++) {
            //    if (result['diffcommits'][i]['filename'] == result['docstring_results'][1][k][0]) {
            if( result['docstring_results'][1][k][2] == 'checked' ){
                docissues = 0;
                for (var m = 0; m < result['docstring_results'][1][k][1].length; m++) {
                    if( result['docstring_results'][1][k][1][m].result.length > 0 ){
                        docissues += result['docstring_results'][1][k][1][m].result.length;
                    }
                }

                doctable.append("<tr><td>" +
                    "<a href='/dashboard/filex/"+project+"?filename="+result['docstring_results'][1][k][0]+"&branch="+branch+"'>"+result['docstring_results'][1][k][0] +"</a>"+
                    "</td><td>" +
                        (docissues < 0 ? '-' : docissues) +
                    "</td><td>" +
                        docbuttons +
                    "</td></tr>");
            }

            if( docissues > 0 )
                $("#docwarning").show();
            
        }
        for (var k = 0; k < result['docstring_results'][1].length; k++) {
            var docbuttons = "";
            docbuttons += "<button class='btn btn-sm btn-primary' onclick='showDocEditor(\"" + result['docstring_results'][1][k][0] + "\",\"" + "DIFF STUFF TO GO HERE" + "\");'>View File in Editor</button><br/>";
 
            if( result['docstring_results'][1][k][2] != 'checked' ){
                docissues = 0;
                for (var m = 0; m < result['docstring_results'][1][k][1].length; m++) {
                    if( result['docstring_results'][1][k][1][m].result.length > 0 ){
                        docissues += result['docstring_results'][1][k][1][m].result.length;
                    }
                }

                doctable.append("<tr><td>" +
                    "<a href='/dashboard/filex/"+project+"?filename="+result['docstring_results'][1][k][0]+"&branch="+branch+"'>"+result['docstring_results'][1][k][0] +"</a>"+
                    "</td><td>" +
                        result['docstring_results'][1][k][2] +
                    "</td><td>" +
                        docbuttons +
                    "</td></tr>");
            }
            
        }
*/

        var testtable = $("#testtable > tbody");
        testtable.empty();

        var testmap = new Map();
/*
        for (var k = 0; k < result['docstring_results'][1].length; k++) {
            //if (result['diffcommits'][i]['filename'] == result['docstring_results'][1][k][0]) {
                for (var m = 0; m < result['docstring_results'][1][k][1].length; m++) {
                    if( result['docstring_results'][1][k][1][m].test_info && result['docstring_results'][1][k][1][m].test_info.length > 0 ){
                        for (var n = 0; n < result['docstring_results'][1][k][1][m].test_info.length; n++) {
                        
                            result['docstring_results'][1][k][1][m].test_info[n][0] //folder
                            result['docstring_results'][1][k][1][m].test_info[n][1] //test filename
                            result['docstring_results'][1][k][1][m].test_info[n][2] //line number

                            var fullfilename = result['docstring_results'][1][k][1][m].test_info[n][0]+"/"+result['docstring_results'][1][k][1][m].test_info[n][1];

                            if( !testmap.has(fullfilename) ){
                                testmap.set(fullfilename,0);
                            }

                            testmap.set(fullfilename,testmap.get(fullfilename)+1);

                        }
                    }
                }
            //}
        }
*/

        if( testmap.size < 1 ){
            testtable.append("<tr><td colspan='3'>"+
                    "<i>This project is not supported yet.</i>"+
                "</td></tr>");
        }

        testmap.forEach((value,key)=>{
            console.log(key + " - " + value);

            if( value > 0 )
                $("#testwarning").show();

            testtable.append("<tr><td>" +
                "<a href='/dashboard/filex/"+project+"?filename="+key+"&branch="+branch+"'>"+key +"</a>"+
                "</td><td>" +
                value +
                "</td><td>" +
                "<button class='btn btn-sm btn-primary' onclick='showTestEditor(\"" + key + "\",\"" + "TEST STUFF TO GO HERE" + "\");'>View File in Editor</button>"+
                "</td></tr>");
        });



        
        var devtable = $("#devtable > tbody");
        devtable.empty();

        for (var i = 0; i < result['merged_dev_table'].length; i++) {

           devtable.append("<tr><td>" +
                result['merged_dev_table'][i]['author'] +
                "</td><td>" +
                "<button class='btn btn-xs btn-success' onclick='sendInvite(\"" + result['merged_dev_table'][i]['author'].substring(result['merged_dev_table'][i]['author'].indexOf(" - ")+3) + "\", \"" + result['merged_dev_table'][i]['filenames'].join(' ') + "\");'>Send&nbsp;Invite</button>"+
                "</td><td>" +
                result['merged_dev_table'][i]['number_commits'] +
                "</td><td>" +
                result['merged_dev_table'][i]['lines'] +
                "</td><td>" +
                result['merged_dev_table'][i]['most_recent_commit'] +
                "</td><td>" +
                "<a href='" + result['source_url'] +"/commit/"+ result['merged_dev_table'][i]['commit_link'] + "'>View on GitHub</a>"+
                "</td></tr>");

        }


        //Collect filename to send to the author recommender tool.
        let fileNames = [];
        for (var i = 0; i < result['diffcommits'].length; i++) {
            var filename = result['diffcommits'][i]['filename'];
            fileNames.push(filename);
        }
        populateView(fileNames);



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


/*
 
 Testing drag and drop

*/

/* draggable element */
const items = document.querySelectorAll('.item');

items.forEach(item => {
    item.addEventListener('dragstart', dragStart);
    item.addEventListener('dragend', dragEnd);
});

function dragStart(e) {
    console.log("dragStart");
    e.dataTransfer.setData('text/plain', e.target.id);
    setTimeout(() => {
        e.target.classList.add('hide');
    }, 0);
}

function dragEnd(e) {
    console.log("dragEnd");
    //setTimeout(() => {
        e.target.classList.remove('hide');
    //}, 0);
}


/* drop targets */
const boxes = document.querySelectorAll('.box');

boxes.forEach(box => {
    box.addEventListener('dragenter', dragEnter)
    box.addEventListener('dragover', dragOver);
    box.addEventListener('dragleave', dragLeave);
    box.addEventListener('drop', drop);
});


function dragEnter(e) {
    e.preventDefault();
    if( e.target.classList.contains('box') )
        e.target.classList.add('drag-over');
}

function dragOver(e) {
    e.preventDefault();
    if( e.target.classList.contains('box') )
        e.target.classList.add('drag-over');
}

function dragLeave(e) {
    e.target.classList.remove('drag-over');
}

function drop(e) {
    console.log("drop");
    console.log(e.target);

    // can as if box or item.  If item, glue items together?
    // but then how to separate items?

    if( e.target.classList.contains('box') ){

        e.target.classList.remove('drag-over');

        // get the draggable element
        const id = e.dataTransfer.getData('text/plain');
        const draggable = document.getElementById(id);

        // add it to the drop target
        e.target.appendChild(draggable);

        // display the draggable element
        draggable.classList.remove('hide');

        // If dropped into PR's tags, then upload the change
        if( e.target.id == 'prtags' ){
            var tags = [];
            for(child of e.target.children ){
                if( child.innerHTML.indexOf('<input') >= 0 )
                    tags.push(child.firstChild.value);
                else    
                    tags.push(child.innerHTML);
            }
        
            console.log(tags);
            saveTags(tags);
        }else{
            var tags = [];
            for(child of document.getElementById('prtags').children )
                tags.push(child.innerHTML);
        
            console.log(tags);
            saveTags(tags);
        }


    }
}

function saveTags(tags){

    console.log("Save PR Tags");
    console.log(tags);

    $.ajax({
        url: '/dashboard/updatetags/', type: 'POST', data: { 'pr': pr, 'tags': tags.toString()}, success: function (result) {
            console.log("got tags response");
            console.log(result);

            //alert('Invite sent to developer.');
        }
    });

    return true;
}