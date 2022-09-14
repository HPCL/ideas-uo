$(document).ready(function () {

    const files = JSON.parse(document.getElementById('files').textContent);
    const subscriptions = JSON.parse(document.getElementById('subscriptions').textContent);

    function sortedIndex(array, value) {
        var low = 0,
            high = array.length;

        while (low < high) {
            var mid = Math.floor((low + high) / 2);
            if (array[mid].text < value) low = mid + 1;
            else high = mid;
        }
        return low;
    }

    function createTreeFromFilePaths(filePaths, projectName) {

        // Tree node structure

        // {
        //   "id": "unique_ID",
        //   "text": "node-0",
        //   "attributes": {},
        //   "children": [],
        //   "checked": true
        // }

        const rootNode = {
            id: projectName,
            text: projectName,
            children: [],
            checked: false,
        }

        let nodeId = 0;
        function insertFileIntoTree(filePath) {
            const pathList = filePath.split('/');
            const fileName = pathList[pathList.length - 1];
            let currentNode = rootNode;

            for (let text of pathList) {
                let foundIndex = currentNode.children.findIndex(child => child.text === text);
                if (foundIndex > -1) { // Found partial path, keep exploring until path different
                    currentNode = currentNode.children[foundIndex];
                    continue;
                } else { // Partial path not Found, create new Nodes until fileName
                    const newNode = {
                        // id must be the fileName if it's a leaf node. 
                        // This way, "values" parameter from treejs knows
                        // which leaf nodes to check.
                        id: text === fileName ? filePath : nodeId++,
                        text,
                        children: [],
                        attributes: {
                            leaf: text === fileName,
                        }
                    };

                    const insertIndex = sortedIndex(currentNode.children, newNode.text);
                    currentNode.children.splice(insertIndex, 0, newNode);
                    currentNode = newNode;
                }
            }
        }

        for (let filePath of filePaths) {
            insertFileIntoTree(filePath);
        }

        return rootNode.children;
    }

    function debounce(func, ms) {
        let timeout;
        return function () {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, arguments), ms);
        };
    }

    function uniques(array1, array2) {
        // Returns single array with all unique elements from array1 and array2
        // array1, array2 are arrays of strings
        const uniquesArray = Array.from(array1);
        for (let elem of array2) {
            if (uniquesArray.includes(elem)) continue;
            uniquesArray.push(elem);
        }
        return uniquesArray;
    }

    const treeData = {}
    const selection = {}
    let selectedProject;
    for (let project in files) {
        treeData[project] = createTreeFromFilePaths(files[project], project);
        if (!subscriptions.hasOwnProperty(project)) {
            selection[project] = [];
        } else {
            selection[project] = subscriptions[project];
        }
    }

    function updateElements() {
        // This function is to be used within the Treejs options.
        // "this" should refer to the Tree object.
        const selectedNodes = this.selectedNodes.filter(node => node?.attributes?.leaf).map(node => node.id);
        console.log(selectedProject, selection);
        selection[selectedProject] = uniques(selection[selectedProject], selectedNodes);
        $('#subscriptions-input').val(JSON.stringify(selection));
    }

    $('#file-filter').keyup(debounce(function () {
        if (!selectedProject) return;
        const filteredFiles = files[selectedProject].filter(file => file.toLowerCase().includes($('#file-filter').val().toLowerCase()));
        if (filteredFiles.length === 0) {
            $('#tree-view').text('No files found matching: ' + $('#file-filter').val());
            return;
        }
        const filteredTreeData = createTreeFromFilePaths(filteredFiles, selectedProject);
        new Tree('#tree-view', {
            data: filteredTreeData,
            closeDepth: 0,
            onChange: updateElements,
            values: selection[selectedProject],
        });
    }, 500));

    $('#project-select').change(function () {
        selectedProject = $(this).val();
        new Tree('#tree-view', {
            data: treeData[selectedProject],
            closeDepth: 1,
            onChange: updateElements,
            values: selection[selectedProject],
        });
    });
});