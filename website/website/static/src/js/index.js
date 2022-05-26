import $ from 'jquery';

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
