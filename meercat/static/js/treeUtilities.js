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

function createTreeFromFilePaths(filePaths) {

    // Tree node structure

    // {
    //   "id": "unique_ID",
    //   "text": "node-0",
    //   "attributes": {},
    //   "children": [],
    //   "checked": true
    // }

    const rootNode = {
        id: 'rootNode',
        text: 'rootNode',
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
            } else { // Partial path not Found, create new Nodes until fileName is reached
                const isLeaf = text === fileName;
                const newNode = {
                    // id must be the filePath if it's a leaf node. 
                    // This way, "values" parameter from treejs knows
                    // which leaf nodes to check.
                    id: isLeaf ? filePath : nodeId++,
                    text,
                    children: [],
                    attributes: {
                        leaf: isLeaf,
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
        if (!uniquesArray.includes(elem)) {
            uniquesArray.push(elem);
        }
    }
    
    return uniquesArray;
}