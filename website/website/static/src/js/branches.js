import $ from 'jquery';

console.log("javascript is working...");

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