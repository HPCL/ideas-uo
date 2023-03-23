jQuery(function () {

    // The "files" and "subscriptions" objects have the following structure with zero or more project_names: 
    // { project_name: [<list of files paths in project>] }
    const files = JSON.parse(document.getElementById('files').textContent);
    const subscriptions = JSON.parse(document.getElementById('subscriptions').textContent);

    // projectTrees: stores the tree data structure for each project
    const projectTrees = {}
    let selectedProject;

    for (let project in files) {
        projectTrees[project] = createTreeFromFilePaths(files[project]);
        
        if (!subscriptions.hasOwnProperty(project)) {
            subscriptions[project] = [];
        }
    }

    function updateElements() {
        // function used in Tree constructor.
        // "this" refers to the Tree object.
        const selectedNodes = this.selectedNodes.filter(node => node?.attributes?.leaf).map(node => node.id);

        // Updating a checkbox could add many elements from the subscription list
        // 
        subscriptions[selectedProject] = uniques(subscriptions[selectedProject], selectedNodes);
        $('#subscriptions-input').val(JSON.stringify(subscriptions));
    }

    $('#file-filter').keyup(debounce(function () {
        if (!selectedProject) return;
        const filteredFiles = files[selectedProject].filter(file => file.toLowerCase().includes($('#file-filter').val().toLowerCase()));
        if (filteredFiles.length === 0) {
            $('#tree-view').text('No files found matching: ' + $('#file-filter').val());
            return;
        }
        const filteredProjectTree = createTreeFromFilePaths(filteredFiles, selectedProject);
        new Tree('#tree-view', {
            data: filteredProjectTree,
            closeDepth: 0,
            onChange: updateElements,
            values: subscriptions[selectedProject],
        });
    }, 500));

    $('#project-select').change(function () {
        selectedProject = $(this).val();
        new Tree('#tree-view', {
            data: projectTrees[selectedProject],
            closeDepth: 1,
            onChange: updateElements,
            values: subscriptions[selectedProject],
        });
    });
});