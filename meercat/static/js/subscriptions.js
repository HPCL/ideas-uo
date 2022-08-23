$(document).ready(function () {

    const files = JSON.parse(document.getElementById('files').textContent);
    const subscriptions = JSON.parse(document.getElementById('subscriptions').textContent);

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

        return rootNode;
    }

    const treeData = {}
    const selection = {}
    for (let project in files) {
        treeData[project] = createTreeFromFilePaths(files[project], project);
        selection[project] = subscriptions[project] ?? [];
    }

    $('#project-select').change(function () {
        project = $(this).val();
        const tree = new Tree('#tree-view', {
            data: treeData[project].children,
            closeDepth: 1,
            onChange: function () {
                const selected = this.selectedNodes.filter(node => node?.attributes?.leaf).map(node => node.id);
                selection[project] = selected;
                $('#subscriptions-input').val(JSON.stringify(selection));
            },
            values: selection[project]
        });
    });
});