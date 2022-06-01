console.log("javascript is working...");

var startdate = $("#startdate");
var date = new Date(new Date().getTime() - (1000 * 60 * 60 * 24 * 30));
startdate.val(date.toISOString().substr(0, 10));

var enddate = $("#enddate");
date = new Date();
enddate.val(date.toISOString().substr(0, 10));


var queryString = window.location.search;
var urlParams = new URLSearchParams(queryString);
var pid = urlParams.get('pid')
console.log(pid);

var editor = CodeMirror.fromTextArea(document.getElementById("demotext"), {
    lineNumbers: true,
    mode: "text/x-python", //"text/x-c++src", //"text/html",
    matchBrackets: true,
    spellcheck: true,
    autocorrect: true,
    styleSelectedText: true
});

let file = `#Adding this comment to just test committing and diff data
def sub(x,y):
  """
  Return the subtraction of two numbers::

  .. math:: '\mathtt{x} - \mathtt{y}'

  Parameters
  ----------
  x: int, real, complex
     first operand
  y: int, real, complex
     second operand
  round: positive int, optional
     If None, does no rounding. Else rounds the result to places specified, e.g., 2.

  Returns
  -------
  z: int, real, complex
      the result of subtraction

  Raises
  ------
  ValueError:
      when 'x' or 'y' is not a number

  See Also
  --------
  Of course, subtraction is built-in to Python as minus sign.

  Notes
  -----
  The algorithm is a straightforward implementation of
  subtraction.

  References
  ----------
  .. [1] Any textbook on mathematics.
  Examples
  --------
  >>> sub(1,2)
  -1
  >>> sub(.03333, .01111)
  .02222
  >>> sub(.03333, .01111, round=3)
  .022
  """
  return x-y

  def list_sub(list1, list2):
    assert len(list1)==len(list2)
    new_list = [sub(x,y) for x,y in zip(list1, list2)]
    return new_list
  `;

editor.setValue(file);
editor.markText({ line: 4, ch: 9 }, { line: 4, ch: 24 }, { className: "styled-background" });
editor.markText({ line: 6, ch: 12 }, { line: 6, ch: 22 }, { className: "styled-background" });

function refreshProject() {
    console.log("refreshing project...");

    if ($('#refreshbutton').hasClass('disabled')) {
        return false;
    } else {

        $('#refreshbutton').addClass('disabled');
        $('#spinner').show();

        $.ajax({
            url: '/dashboard/refreshproject', data: { 'pid': pid }, success: function (result) {
                console.log("success ajax");
                console.log(result);

                //refresh the page here
                location.reload();

            }
        });
    }
}

function patchFile() {

    console.log(editor.getValue());


    $.ajax({
        url: '/dashboard/createpatch', data: { 'pid': pid, 'filename': 'folder1/arithmetic.py', 'filecontents': editor.getValue() }, success: function (result) {

            console.log("success ajax");
            console.log(result);

            var element = document.createElement('a');
            element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(result.patch));
            element.setAttribute('download', 'arithmetic.py.patch');

            element.style.display = 'none';
            document.body.appendChild(element);

            element.click();

            document.body.removeChild(element);
        }
    });

}
