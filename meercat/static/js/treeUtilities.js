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

function* infinite() {
    let index = 0;
  
    while (true) {
        yield index++;
    }
}
  

function insertFileIntoTree(node, filePath, generator, errors = null) {
    const pathList = filePath.split('/');
    const fileName = pathList[pathList.length - 1];

    for (let text of pathList) {
        let foundIndex = node.children.findIndex(child => child.text === text);
        if (foundIndex > -1) { // Found partial path, keep exploring until path different
            node = node.children[foundIndex];
                    
            if (errors !== null) {
                node.attributes.error = errors;
            }
        } else { // Partial path not Found, create new Nodes until fileName is reached
            const isLeaf = text === fileName;
            const newNode = {
                // id must be the filePath if it's a leaf node. 
                // This way, "values" parameter from treejs knows
                // which leaf nodes to check.
                id: isLeaf ? filePath : generator.next().value,
                text,
                children: [],
                attributes: {
                    leaf: isLeaf,
                }
            };
                    
            if (errors!== null) {
                newNode.attributes.error = errors;
            }

            const insertIndex = sortedIndex(node.children, newNode.text);
            node.children.splice(insertIndex, 0, newNode);
            node = newNode;
        }

    }
}


// Tree node structure

// {
//   "id": "unique_ID",
//   "text": "node-0",
//   "attributes": {},
//   "children": [],
//   "checked": true|false
// }

function createTreeFromResults(results) {
    const rootNode = {
        children: [],
    }

    const generator = infinite();

    for (let result of results) {
        insertFileIntoTree(rootNode, result.filePath, generator, result.errors);
    }

    return rootNode.children;
}

function createTreeFromFilePaths(filePaths) {


    const rootNode = {
        children: [],
    }

    const generator = infinite();

    for (let filePath of filePaths) {
        insertFileIntoTree(rootNode, filePath, generator);
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