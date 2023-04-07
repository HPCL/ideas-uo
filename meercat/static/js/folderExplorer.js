$(document).ready(function () {

    const files = JSON.parse(document.getElementById('files').textContent);
    const results = JSON.parse(document.getElementById('results').textContent);

    let fileTree;
    if (results.length) {
        fileTree = createTreeFromResults(results);
        console.log(results);
        console.log(fileTree);
        new Tree('#tree-view', {
            data: fileTree,
            closeDepth: 1,
        });
    } else {
        let selection = []

        function updateElements() {
            // This function is to be used within the Treejs options.
            // "this" refers to the Tree object.
            const selectedNodes = this.selectedNodes.filter(node => node?.attributes?.leaf).map(node => node.id);
            selection = uniques(selection, selectedNodes);
            $('#unit-selection').val(JSON.stringify(selection));
        }

        fileTree = createTreeFromFilePaths(files);

        new Tree('#tree-view', {
            data: fileTree,
            closeDepth: 1,
            onChange: updateElements,
        });

        $('#file-filter').keyup(debounce(function () {
            const filteredFiles = files.filter(file => file.toLowerCase().includes($('#file-filter').val().toLowerCase()));
            if (filteredFiles.length === 0) {
                $('#tree-view').text('No files found matching: ' + $('#file-filter').val());
                return;
            }
            const filteredTreeData = createTreeFromFilePaths(filteredFiles);
            new Tree('#tree-view', {
                data: filteredTreeData,
                closeDepth: 1,
                onChange: updateElements,
                values: selection,
            });
        }, 500));
    }
    
});