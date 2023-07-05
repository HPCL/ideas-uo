const SEPARATOR = '/';

/**
 * Class with static utility functions to handle path manipulation.
 * Paths are represented as strings and hold no state, so there is no need to instantiate Path objects.
 * Paths can be relative or absolute. 
 * A path is considered valid if and only if its first and last character are not SEPARATOR.
 */
class Path {

    /**
     * Finds the longest common path between two file paths.
     * @example
     * Path.commonPrefix('a/b/c', 'a/b/d') // returns 'a/b'
     * Path.commonPrefix('c/d/a', 'a/b/d') // returns empty string
     * @param {string} path1 represents a valid file path
     * @param {string} path2 represents a valid file path
     * @returns the longest matching common prefix
     */
    static commonPrefix(path1, path2) {
        let i = 0;
        while (i < path1.length && i < path2.length && path1[i] === path2[i]) { // compare char by char
            i += 1;
        }

        /**
         * If there is a common prefix, the resulting substring will have a trailing slash, 
         * which is removed by edcrementing the slice index. If there is no match i will be 0 and i - 1
         * will be -1, but the call to slice is still safe.
         */
        return path1.slice(0, i - 1);  
    }

    /**
     * Finds the file path that results from taking subPath away from path. If path is not a file path within subPath, subPath is returned.
     * @param {string} path directory within subPath
     * @param {string} subPath parent directory of path
     * @returns the file path that results from taking subPath away from path, or subPath if path is not a file path within subPath.
     */
    static trailingPath(path, subPath) {
        // Check if subPath is not a file path within path
        if (!subPath || !path.includes(SEPARATOR) || !path.includes(subPath)) return path;

        return path.slice(subPath.length + 1); // the +1 is needed to return a new file path beginning without a slash
    }

    /**
     * Get the last substring in path after the last forward slash
     * @param {string} path a file path
     * @returns the substring in path after the last forward slash
     */
    static baseName(path) {
        let crumbs = path.split(SEPARATOR);
        let tail = crumbs.pop();
        return tail;
    }

    /**
     * Gets the list of substrings in path separated by a forward slash
     * @param {string} path a file path
     * @returns a list of strings that results from spliting path with the forward slash
     */
    static crumbs(path) {
        return path.split(SEPARATOR);
    }

    /**
     * Joins path1 and path2 with a forward slash an returns the result.
     * @param {string} path1 a file path
     * @param {string} path2 a file path
     * @returns The file path path1/path2. If one path is empty, the other path is returned.
     */
    static join(path1, path2) {
        if (path1 === '') return path2;
        if (path2 === '') return path1;

        return [path1, path2].join(SEPARATOR);
    }
}

/**
 * Class for saving the state of a node in the file tree. TreeNode objects correspond to nodes in the file tree.
 * Paths in TreeNode are relative to the project root and are a unique id for every tree node in the file tree.
 */
class TreeNode {
    /**
     * @param {TreeNode} parent Points the the parent of this node. The root node has its parent set to null.
     * @param {string} path the file path of the tree node relative to the project root.
     * @param {object} metrics (optional) metrics for the node provided by meercat. The object must have the exact same properties
     *                         as the ones in the default object set below.
     */
    constructor({ parent, path, metrics }) {
        this.metrics = metrics? 
        metrics // If metrics are provided in the object paramter, use them. set default values otherwise.
        :
        {
            documentation: {
                total: 0,
                missing: 0,
                issues: 0
            },
            busFactor: 0,
            linter: 0
        };
        this.parent = parent;
        this.path = path;
        this.label = Path.baseName(path);
        this.children = []; // List of TreeNodes populated when the tree is contructed
        /**
         * Indicates if the node sends notifications to the user when appearing on pull requests. A leaf node can only be true or false.
         * A folder can be true, meaning the user gets notified for all its descendants on pull requests; false, meaning the user does 
         * not get notifications for any node under this node; or null, meaning the user gets notified about some nodes but not all.
         */
        this.subscribed = false;
        /**
         * Indicates if this node is not grayed out. Grayed out nodes (visibile = false) are not considered for averaging metrics
         * and are not considered in the events found in DataBinder.
         */
        this.visible = true; 
    }

    /**
     * Looks for a child node of this node whose file path is path.
     * @param {string} path a file path relative to the project root
     * @returns A TreeNode object corresponding to path that is a descendant of this node if found, otherwise null.
     */
    getChild(path) {
        for (let child of this.children) {
            if (child.path === path) {
                return child;
            }
        }

        return null;
    }

    /**
     * Determines if this node has a child with its file path equal to the path provided
     * @param {string} path a file path relative to the project root
     * @returns true if this node has a child whose file path equals path
     */
    hasChild(path) {
        return this.children.some(child => child.path === path);
    }

    /**
     * Gets a desendant of this node whose file path equals the path provided
     * @param {string} path a file path relative to the project root
     * @returns a descendant node of this path if exists, null otherwise.
     */
    getDescendant(path) {
        // Separate path into two components: this node's path and the pah following the parameters' path.
        let commonPrefix = Path.commonPrefix(this.path, path);
        let trailingPath = Path.trailingPath(path, commonPrefix);

        const trailingCrumbs = Path.crumbs(trailingPath);
        let currentPath = commonPrefix;
        let descendant = this;

        // Look for descendant by visiting descendant nodes until the descendant is reached.
        for (let crumb of trailingCrumbs) {
            currentPath = Path.join(currentPath, crumb);
            descendant = descendant.getChild(currentPath);

            if (descendant === null) break; // if path does not exist in tree it will return null
        }

        return descendant;
    }

    /**
     * Adds a child to this node.
     * @param {TreeNode} node The node to be added as a child of this node
     */
    addChildNode(node) {
        this.children.push(node);
    }

    /**
     * Determine if this node is a leaf node by checking its children
     * @returns wether this node is a leaf node
     */
    isLeaf() {
        return this.children.length === 0;
    }

    /**
     * Adds achild Node with the subtree built from path.
     * @param {string} path a file path relative to the project root
     * @param {object} metrics a metric objects as defined in the constructor of this class
     */
    insert(path, metrics) {
        const crumbs = Path.crumbs(path);

        let currentPath = this.path;
        let node = this;
        let child;
        for (let crumb of crumbs) {
            currentPath = Path.join(currentPath, crumb);
            child = new TreeNode({ parent: node, path: currentPath });
            node.addChildNode(child);
            node = child;
        }

        if (metrics) node.metrics = metrics;
    }

    /**
     * Recuresively updates the subscription status for this node's parents based on the status of its sibling. Stops at the root node.
     * 
     * @returns nothing
     */
    updateParentSubscriptions() {
        // this return is needed to stop the recursion on the root node for some reason.
        if (this.parent === null) return;

        // count number of siblings and their subscritpion status
        const SubscribedSiblingCount = this.parent.children.reduce((count, child) => child.subscribed? count + 1 : count, 0);
        const nullSiblingCount = this.parent.children.reduce((count, child) => child.subscribed === null? count + 1: count, 0);
        const siblingCount = this.parent.children.length;

        if (nullSiblingCount > 0) { // Some siblings have null subscription status, meaning the parents gets null subscritpion too.
            this.parent.subscribed = null;
        } else if (SubscribedSiblingCount === siblingCount) { // all child nodes of this node's parent have its subscription set to true
            this.parent.subscribed = true;
        } else if (SubscribedSiblingCount === 0) { // all child nodes of this node's parent have its subscription set to false
            this.parent.subscribed = false;
        } else {
            this.parent.subscribed = null;
        }

        if (this.parent !== null) { // keep recursion if root node has not been reached.
            this.parent.updateParentSubscriptions();
        }
    }

    /**
     * changes the subscription of all descendant nodes based on the subscription value for this node.
     * @returns nothing
     */
    updateSubtreeSubscriptions() {
        /**
         * updateSubtreeSubscriptions: changes the subscription based on the current subscription value for "this".
         */
        
        // Case: neither this node nor nodes under it (if any) are in the subscriptions. The following code adds all files
        // in the subtree rooted in the current node to the subscriptions.
        if (!this.subscribed && this.subscribed !== null) {
            for (let node of this) {
                if (node.visible) node.subscribed = true;
            }
            return;
        }

        // Case: Some nodes under this node are in the subcsriptions (only folders can have null subscribed value). The following code
        // removes every file under this folder from the subcsriptions.
        if (this.subscribed === null) {
            let confirmed = confirm("This action will stop notifications from every file and folder underneath it. Continue?");
            if (!confirmed) return;
        }

        // Case: this node and all nodes under it (if any) have a subscription. The following code removes all files in the subtree
        // rooted in the current node from the subscriptions.
        for (let node of this) {
            node.subscribed = false;
        }
    }

    /**
     * updates subscriptions for ancestry and descendants based on the value of this node.
     */
    updateSubscriptions() {
        this.updateSubtreeSubscriptions();
        this.updateParentSubscriptions();
    }

    /**
     * Finds and returns the node matching the path parameter at the deepest level of the file tree.
     * @example
     * getDeepestMatchingNode('a/b/c/d/e') // if the file tree has a leaf node with path 'a/b/c', return that node
     * getDeepestMatchingNode('a/b/c/d/e') // if the file tree has a leaf node with path 'a/b/c', return that node
     * getDeepestMatchingNode('a/b/c') // if the file tree has no node starting with 'a', return the root node
     * @param {string} path a file path relative to the root project
     * @returns the node that has the deepest match with the path parameter in the file tree.
     */
    getDeepestMatchingNode(path) {
        let crumbs = Path.crumbs(path);

        let node = this;
        let currentPath = '';
        for (let crumb of crumbs) {
            currentPath = Path.join(currentPath, crumb);
            if (!node.hasChild(currentPath)) break;
            node = node.getChild(currentPath);
        }

        return node;
    }

    /**
     * iterates over this node all descendant nodes. This is a JavaScript feature to make TreeNode iterable.
     */
    *[Symbol.iterator]() {
        const nodesStack = [...this.children];
        let currentNode;
        yield this;
        while (nodesStack.length > 0) {
            currentNode = nodesStack.pop();
            yield currentNode;
            nodesStack.push(...currentNode.children);
        }
    }

    /**
     * 
     * @returns all descendant nodes, including this node, that have subscription set to true
     */
    getSubscribedNodePaths() {
        let subscribedNodePaths = [];
        for (let node in this) {
            if (node.isLeaf() && node.subscribed) subscribedNodePaths.push(node.path);
        }
        return subscribedNodePaths;
    }

    /**
     * Calculates the metrics aggregation (average for now) for non-leaf nodes and their visibility.
     * @returns nothing to stop recursion
     */
    computeMetrics() {
        if (!this.children.length) {
            this.visible = this.label.endsWith('.F90');
            return;
        }

        let visible = false;
        let childrenWithMetrics = 0;
        for (let child of this.children) {
            child.computeMetrics();
            visible = visible || child.visible;
            if (child.visible) childrenWithMetrics += 1;
            this.metrics.documentation.total += child.metrics.documentation.total;
            this.metrics.documentation.missing += child.metrics.documentation.missing;
            this.metrics.documentation.issues += child.metrics.documentation.issues;
            this.metrics.busFactor += child.metrics.busFactor;
            this.metrics.linter += child.metrics.linter;
        }

        this.visible = visible;
        if (childrenWithMetrics === 0) return;
        this.metrics.documentation.total = Math.round(this.metrics.documentation.total / childrenWithMetrics);
        this.metrics.documentation.missing = Math.round(this.metrics.documentation.missing / childrenWithMetrics);
        this.metrics.documentation.issues = Math.round(this.metrics.documentation.issues / childrenWithMetrics);
        this.metrics.busFactor = Math.round(this.metrics.busFactor / childrenWithMetrics);
        this.metrics.linter = Math.round(this.metrics.linter / childrenWithMetrics);
    }
}

/**
 * Class with static utility functions to render TreeNodes.
 */
class FileTreeLi {
    /**
     * Creates and return an image DOMElement with the properties specified in the parameters
     * @param {string} src image source for the icon
     * @param {string} alt alt message for the icon
     * @param {Array} classList Array of strings with html classes for the icon
     * @returns an image DOMElement with the desired attributes
     */
    static createIcon(src, alt, classList) {
        const icon = document.createElement('img');
        icon.src = src;
        icon.alt = alt;

        icon.classList.add(...classList);

        return icon;
    }

    /**
     * Create and return an image DOMElement wrapped in a helper class to display before a label in the rendered file tree.
     * This function is used for garyed out icons.
     * @param {string} src image source for the icon
     * @param {string} alt alt message for the icon
     * @param {Array} classList Array of strings with html classes for the image
     * @returns a div DOMElement wrapping an image element
     */
    static createPreLabelIcon(src, alt, classList) {
        const icon = document.createElement('img');
        icon.src = src;
        icon.alt = alt;

        icon.classList.add(...classList);


        const iconWrapper = document.createElement('div');
        iconWrapper.classList.add('file-tree-icon-wrapper');
        iconWrapper.append(icon);

        return iconWrapper;
    }

    /**
     * Creates an image DOMElement next to a span element with a metric number and returns them wrapper in a div
     * @param {number} metric a number for the metric that this icon represents
     * @param {string} src image source for the icon
     * @param {string} alt alt message for the icon
     * @returns an image with a wrapper that overlays it when stylized with css
     */
    static createMetricIcon(metric, src, alt) {
        const icon = document.createElement('img');
        icon.src = src;
        icon.alt = alt;

        icon.classList.add('pre-label-icon', `error-${Math.floor(metric * 3 / 101)}`);

        const iconMetric = document.createElement('span');
        iconMetric.textContent = metric;
        iconMetric.classList.add('pre-label-icon-metric');

        const iconWrapper = document.createElement('div');
        iconWrapper.classList.add('file-tree-icon-wrapper');
        iconWrapper.append(icon, iconMetric);

        return iconWrapper;
    }

    /**
     * Constructs the DOM elements needed to display a file tree node information in the browser
     * @param {TreeNode} treeNode a TreeNode object
     * @returns a div DOMElement with all nested elements needed to display a tree node in the li element
     */
    static render(treeNode) {

        const wrapper = document.createElement('div');

        const nodeLabel = document.createElement('span');
        if (treeNode.visible) nodeLabel.classList.add(['node-label']);
        nodeLabel.textContent = treeNode.label;

        let icons;
        if (!treeNode.visible) { // grays out the node element
            wrapper.classList.add(['grayed-out']);
            icons = [
                FileTreeLi.createPreLabelIcon('/static/images/documentation-icon.png', 'documenatation metric', ['pre-label-icon', 'grayed-out-icon']),
                FileTreeLi.createPreLabelIcon('/static/images/bus-factor-icon.png', 'bus factor metric', ['pre-label-icon', 'grayed-out-icon']),
                FileTreeLi.createPreLabelIcon('/static/images/linter-icon.png', 'Linter metric', ['pre-label-icon', 'grayed-out-icon']),
            ];
        } else {
            icons = [
                FileTreeLi.createMetricIcon(treeNode.metrics.documentation.total, '/static/images/documentation-icon.png', 'documenatation metric'),
                FileTreeLi.createMetricIcon(treeNode.metrics.busFactor, '/static/images/bus-factor-icon.png', 'bus factor metric'),
                FileTreeLi.createMetricIcon(treeNode.metrics.linter, '/static/images/linter-icon.png', 'Linter metric'),
            ];
        }

        // adds subscription icons
        let subscriptionSrc = treeNode.subscribed ? '/static/images/subscription-icon.png' : (treeNode.subscribed === null ? '/static/images/partial-subscription-icon.png' : '');
        let subscriptionAlt = treeNode.subscribed ? 'You will get notifications on pull requests' : (treeNode.subscribed === null ? 'You will get notifications for some iems under this folder on pull requests' : '');
        let subscriptionIcon = FileTreeLi.createIcon(subscriptionSrc, subscriptionAlt, ['post-label-icon']);
        subscriptionIcon.classList.add('subscription-icon');
        subscriptionIcon.onerror = function () { this.style.display = 'none'; }; // empty string on src attribute from image tag displays a broken image icon. This function hides it.

        // Add elements to wrapper
        wrapper.append(...icons, nodeLabel, subscriptionIcon);

        return wrapper;
    }
}

/**
 * Renderer is in charge of rendering the file tree through static utility functions.
 * Due to the large amount of file paths that need to be handled (~10,000) and the folder nodes generated from the file paths, rendered
 * nodes are only rendered when they need to appear. The program takes advantage of the requirement stating that only one folder can
 * be expanded per folder level. When a folder node is expanded, its children are rendered, and their grandchildren are rendered too 
 * but hidden. When a folder node is colsed, all the rendered subtree underneath it is removed from the DOM and its children are
 * rendered again but hidden.
 */
class Renderer {

    /**
     * Creates a DOMElement with the node's information by calling the static render function of the FileTreeLi class.
     * The rendering should change by modifying FileTreeLi's render method or by creating a different class with a render method.
     * @param {TreeNode} treeNode the tree node to render
     * @returns a DOMElement containing the rendered TreeNode
     */
    static createTreeNode(treeNode) {
        return FileTreeLi.render(treeNode);
    }

    /**
     * Render the treeNode infromation in the panel section.
     * @param {TreeNode} treeNode a treeNode to display its information in the panel area.
     */
    static renderPanel(treeNode) {

        const missingDocsBar = document.getElementById('missing-docs-bar');
        const missingDocsMetric = document.getElementById('missing-docs-metric');
        const docIssuesBar = document.getElementById('non-doxy-docs-bar');
        const docIssuesMetric = document.getElementById('non-doxy-docs-metric');
        const linterBar = document.getElementById('linter-bar');
        const linterMetric = document.getElementById('linter-metric');

        /**
         * Metrics are randomly generated with numbers from 0 to 100 and thus need no conversion to percentage when calculating
         * the bar width. If the metrics change, a percentage will have to be calculated.
         */
        missingDocsBar.style.width = treeNode.metrics.documentation.missing + '%';
        /**
         * Bar colors are stylized based on the classes error-0 for a green bar, error-1 for a yellow-bar, and error-2 for a red bar.
         * The following mapping applies based on the calculation:
         *  - 0 <= error-0 <= 33
         *  - 34 <= error-1 <= 67
         *  - 68 <= error-2 <= 100
         * A different mapping will be needed if the metrics change
         */
        missingDocsBar.className = `error-${Math.floor(treeNode.metrics.documentation.missing * 3 / 101)}`;
        docIssuesBar.style.width = treeNode.metrics.documentation.issues + '%';
        docIssuesBar.className = `error-${Math.floor(treeNode.metrics.documentation.issues * 3 / 101)}`;

        missingDocsMetric.textContent = treeNode.metrics.documentation.missing;
        docIssuesMetric.textContent = treeNode.metrics.documentation.issues;

        linterBar.style.width = treeNode.metrics.linter + '%';
        linterBar.className = `error-${Math.floor(treeNode.metrics.linter * 3 / 101)}`;
        linterMetric.textContent = treeNode.metrics.linter;

        // Display file path in panel
        const fileLabel = document.getElementById('path');
        fileLabel.textContent = treeNode.path;
        document.getElementById('hyperlink-icon').style.visibility = 'visible';
        // TODO: construct a link to file explorer or incorporate it to the data sent by the backend

        // Change notification button based on nodes subscription value
        const button = document.getElementById('panel-subscribe-btn');
        button.textContent = !treeNode.subscribed ? 'Notify on pull request' : 'Stop notifications';
        button.dataset.path = treeNode.path;
    }

    /**
     * Render the nodes that are a direct child of th root node (the root node itself is not rendered) according to the rules stated
     * in the documentation of the class
     * @param {TreeNode} treeRoot the root node of the file tree
     * @param {string} DOMRootId id of DOM element where the tree will be rendered as a child
     */
    static renderRoot(treeRoot, DOMRootId) {
        const container = document.getElementById(DOMRootId);
        const div = document.createElement('div');
        div.id = 'file-path-tree';
        container.appendChild(div);
        Renderer.renderChildren(div, treeRoot, true);
        for (let node of treeRoot.children) {
            let DOMNode = document.querySelector('[data-path="' + node.path + '"]');
            Renderer.renderChildren(DOMNode, node);
        }
    }

    /**
     * Create Li element and add it as a child of DOMNode.
     * @param {Element} DOMNode a DOMElement that will add the resulting li element as its child
     * @param {TreeNode} treeNode the tree node to be rendered
     */
    static renderLi(DOMNode, treeNode) {
        const li = document.createElement('li');
        li.dataset.path = treeNode.path;

        if (treeNode.isLeaf()) {
            li.classList.add(['no-switcher']);
        } else {
            const switcher = document.createElement('span');
            switcher.classList.add(['switcher']);
            li.appendChild(switcher);
        }

        const rendered = Renderer.createTreeNode(treeNode);
        rendered.classList.add(['rendered-element']);

        li.appendChild(rendered);
        DOMNode.appendChild(li);
    }

    /**
     * Render all treeNode's children in a ul and add it as a child of DOMNode. If the rendered tree node is not the root,
     * render the children but do not show them.
     * @param {Element} DOMNode DOMElement where the resulting ul will be added as a child
     * @param {TreeNode} treeNode a tree node whose children will be rendered under the resulting ul
     * @param {boolean} root indicates wether the call is being made for the root node or not
     */
    static renderChildren(DOMNode, treeNode, root = false) {
        const ul = document.createElement('ul');
        if (!root) {
            // initially collapsed;
            ul.style.height = 0;
            ul.dataset.collapsed = true;
        }

        for (let node of treeNode.children) {
            Renderer.renderLi(ul, node);
        }

        DOMNode.appendChild(ul);
    }

    //credits to https://css-tricks.com/using-css-transitions-auto-dimensions/
    static collapseSection(element) {
        // get the height of the element's inner content, regardless of its actual size
        let sectionHeight = element.scrollHeight;

        // temporarily disable all css transitions
        let elementTransition = element.style.transition;
        element.style.transition = '';

        // on the next frame (as soon as the previous style change has taken effect),
        // explicitly set the element's height to its current pixel height, so we 
        // aren't transitioning out of 'auto'
        requestAnimationFrame(function () {
            element.style.height = sectionHeight + 'px';
            element.style.transition = elementTransition;

            // on the next frame (as soon as the previous style change has taken effect),
            // have the element transition to height: 0
            requestAnimationFrame(function () {
                element.style.height = 0 + 'px';
            });
        });

        // mark the section as "currently collapsed"
        element.remove();
    }

    static expandSection(element) {

        // get the height of the element's inner content, regardless of its actual size
        let sectionHeight = element.scrollHeight;

        // have the element transition to the height of its inner content
        element.style.height = sectionHeight + 'px';


        // when the next css transition finishes (which should be the one we just triggered)
        element.addEventListener('transitionend', function noHeight(e) {
            // remove "height" from the element's inline styles, so it can return to its initial value
            element.style.height = null;
        }, { once: true });

        // mark the section as "currently not collapsed"
        element.dataset.collapsed = false;
    }

    /**
     * Updates the subscription icon for a single tree node
     * @param {TreeNode} treeNode updates the subscritpion icon of this node
     * @returns nothing
     */
    static updateSubscirptionIcon(treeNode) {
        let subscriptionIcon = document.querySelector('[data-path="' + treeNode.path + '"] > .rendered-element > .subscription-icon');
        // Although nodes under treeNode may have a subscription, it may not be rendered and the check for its existence
        // in the rendered tree is necessary
        if (!subscriptionIcon || !treeNode.visible) return;

        if (treeNode.subscribed === null) {
            subscriptionIcon.src = '/static/images/partial-subscription-icon.png';
            subscriptionIcon.alt = 'You will get notifications for some iems under this folder on pull requests';
            subscriptionIcon.title = 'You will get notifications for some iems under this folder on pull requests';
            subscriptionIcon.style.display = 'inline-block';
        } else if (treeNode.subscribed === true) {
            subscriptionIcon.src = '/static/images/subscription-icon.png';
            subscriptionIcon.alt = 'You will get notifications on pull requests';
            subscriptionIcon.title = 'You will get notifications on pull requests';
            subscriptionIcon.style.display = 'inline-block';
        } else {
            subscriptionIcon.src = '';
            subscriptionIcon.alt = '';
            subscriptionIcon.title = '';
        }
    }

    /**
     * Recursively updates the parent node of the treeNode until the root element is reached.
     * @param {TreeNode} treeNode the child of the DOM parent node to be updated
     * @returns nothing to stop the recursion
     */
    static updateDOMParentSubscriptions(treeNode) {
        if (treeNode.parent === null) return;
        Renderer.updateSubscirptionIcon(treeNode.parent);
        Renderer.updateDOMParentSubscriptions(treeNode.parent);
    }

    /**
     * Updates the subscription icon of treeNode and all its descendants.
     * @param {TreeNode} treeNode a tree node
     */
    static UpdateDOMSubtreeSubscriptions(treeNode) {
        for (let node of treeNode) {
            Renderer.updateSubscirptionIcon(node);
        }
    }
}

/**
 * DataBinder handles the events triggered by interactions with the file tree on the browser.
 */
class DataBinder {
    /**
     * Saves the fileTree as state and renders it in the browser.
     * @param {string} elementId id of the html element where the file tree will be rendered as a child
     * @param {FileTree} fileTree an instance of a FileTree
     */
    constructor(elementId, fileTree) {
        this.fileTree = fileTree;
        Renderer.renderRoot(fileTree.root, elementId);
    }

    /**
     * Delgates the event handling to the relevant function based on what the user interacted with.
     * @param {Event} event a DOM event
     */
    handleEvent(event) {
        if (event.type === 'click') {
            // switcher clicks expand folder nodes
            if (event.target.classList.contains(['switcher'])) {
                this.handleSwitcherClick(event);
            }

            // node-label clicks display information of the clicked node on the panel
            if (event.target.classList.contains(['node-label'])) {
                this.handleNodeLabelClick(event);
            }

            // subscribed the user to the node displayed in the panel
            if (event.target.id === 'panel-subscribe-btn') {
                this.handleSubscriptionClick(event);
            }
        }
    }

    /**
     * Renders the treeNode information in the panel.
     * @param {Event} event the DOM event that triggered this function
     * @returns nothing
     */
    handleNodeLabelClick(event) {
        const liNode = event.target.closest('li');
        const liTreeNode = this.fileTree.root.getDescendant(liNode.dataset.path);

        if (!liTreeNode.visible) return;

        Renderer.renderPanel(liTreeNode);

        const button = document.getElementById('panel-subscribe-btn');
        button.style = 'visibility: visible;';
    }

    /**
     * Expands or collapses the folder next to the clicked switcher if it was collapsed or expanded, respectively.
     * @param {Event} event DOM event that triggered this action
     */
    handleSwitcherClick(event) {
        const liNode = event.target.closest('li');
        const liTreeNode = this.fileTree.root.getDescendant(liNode.dataset.path);
        const liNodeList = liNode.querySelector('ul');
        const parentList = liNode.closest('ul');
        const switcher = event.target;

        // collapsed is false when the folder is expanded.
        if (liNodeList.dataset.collapsed === 'false') {
            Renderer.collapseSection(liNodeList); // collapse the folder's children and remove them from the DOM
            Renderer.renderChildren(liNode, liTreeNode); // Render the folder's children again without showing them
        } else { // case when node was collapsed
            const expandedSiblingLiNodeList = parentList.querySelector('li > ul[data-collapsed="false"]'); // Get expanded sibling folder, if any.
            if (expandedSiblingLiNodeList !== null) { // There was an expande sibling folder.
                const expandedSiblingLiNode = expandedSiblingLiNodeList.closest('li');
                const expandedSiblingTreeNode = this.fileTree.root.getDescendant(expandedSiblingLiNode.dataset.path);
                Renderer.collapseSection(expandedSiblingLiNodeList); // collapse sibling's children
                Renderer.renderChildren(expandedSiblingLiNode, expandedSiblingTreeNode); // render sibling's children without showing them

                const switchers = expandedSiblingLiNode.querySelectorAll('span.switcher.expanded');
                switchers.forEach(switcher => switcher.classList.remove('expanded')); // restore original position of switchers under sibling node
            }

            // Expand folder of node next to the clicked switcher
            Renderer.expandSection(liNodeList);
            for (let child of liTreeNode.children) { // render the children of every child within folder
                let childNode = document.querySelector('[data-path="' + child.path + '"]');
                Renderer.renderChildren(childNode, child);
            }
        }

        switcher.classList.toggle('expanded'); // change the position of the clicked switcher
    }

    /**
     * Update subscriptions generated by the click event and send the resulting subscription list to the backend. Update the front end
     * if the back end saved the list successfully, otherwise, show an error message on the front end.
     * @param {Event} event DOM event that triggered this action
     */
    handleSubscriptionClick(event) {
        const treeNode = this.fileTree.root.getDescendant(event.target.dataset.path);

        // save current subscriptions in case of save failure
        const old_subscriptions = Array.from(this.fileTree.subscriptions); 

        // update watched state on relevant tree nodes
        treeNode.updateSubscriptions();

        // Update subscriptions
        for (let node of treeNode) {
            if (!node.isLeaf()) continue;

            if (node.subscribed) {
                this.fileTree.subscriptions.add(node.path);
            } else {
                this.fileTree.subscriptions.delete(node.path);
            }
        }

        let subscriptions = JSON.stringify(Array.from(this.fileTree.subscriptions)); // stringify subscriptions list
        // set loading message
        const status = document.getElementById("save-status");
        status.innerText = "Loading..."
        event.target.disabled = true; // disable action button

        $.ajax({
            url: '/dashboard/save_subscriptions/', 
            type: 'POST', 
            data: { subscriptions: subscriptions }, 
            success: (result) => {
                if (result.success === "true") { // update DOM elements on success
                    event.target.textContent = !treeNode.subscribed ? 'Notify on pull request' : 'Stop notifications';
                    status.innerText = "notifications updated";

                    Renderer.UpdateDOMSubtreeSubscriptions(treeNode);
                    Renderer.updateDOMParentSubscriptions(treeNode);
                } else { // show error message on failure (due to server error)
                    this.fileTree.subscriptions = old_subscriptions; // restore subscriptions on failure
                    status.innerText = "There was an error saving your notifications";
                    console.error(result.message);
                }
                event.target.disabled = false;
            },
            error: (error) => { //  show error message on failure (due to ajax error)
                this.fileTree.subscriptions = old_subscriptions; // restore subscriptions on failure

                status.innerText = "There was an error saving your notifications";
                console.error(error);
                event.target.disabled = false;
            } 
        });
    }
}

/**
 * Class to save relevant file tree state information.
 */
class FileTree {
    /**
     * Instantiates a file tree with the specified paths, a subscription list that is a subset of paths, and
     * generates random metrics for the file tree.
     * 
     * @param {list} paths list of strings representing file paths
     * @param {list} subscriptions list of paths representing file paths
     */
    constructor(paths, subscriptions = []) {
        this.paths = paths;
        this.subscriptions = new Set(subscriptions);
        this.root = this.generateTreeWithMetrics(paths, this.subscriptions);
    }

    /**
     * Inserts randomly generated metrics and sets the subscription status for the tree nodes based on the subscription list.
     * @param {list} paths a list of file paths
     * @param {list} subscriptions a list of file paths that is a subset of paths
     * @returns the constructed file tree
     */
    generateTreeWithMetrics(paths, subscriptions) {
        // genates random integers between min and max, inclusive.
        function randInt(min, max) {
            return Math.floor(Math.random() * (max - min + 1)) + min;
        }

        /**
         * [{filepath: 'a/b/c', metrics: {
                documentation: {
                    total: 0,
                    missing: 0,
                    issues: 0
                },
                busFactor: 0,
                linter: 0
            }}]
         */

        // create tree root
        const tree = new TreeNode({ parent: null, path: ''});
    
        // insert paths into tree
        for (let path of paths) {
            let insertNode = tree.getDeepestMatchingNode(path); // get the deepest common folder path in tree that matches path
            const trailingPath = Path.trailingPath(path, insertNode.path); // get remainder path afterprevious line

            let missing = randInt(0, 50); // missing documentation metrics
            let issues = randInt(0, 50); // documentation issues metrics
            if (path.endsWith('.F90')) { // insert metrics only if it is an .F90 file
                let metrics = path.endsWith('.F90') ? { documentation: { total: missing + issues, missing, issues }, busFactor: randInt(0, 100), linter: randInt(0, 100) }: null;
                insertNode.insert(trailingPath, metrics);
            } else {
                insertNode.insert(trailingPath);
            }
        }

        // update subscriptions for each file
        for (let path of paths) {  
            if (subscriptions.has(path)) {
                tree.getDescendant(path).updateSubscriptions();
            }
        }

        // aggregate file metrics on folders
        tree.computeMetrics();

        return tree;
    }

}

$(document).ready(function() {

    // parse paths and subscriptions lists
    const paths = JSON.parse(document.getElementById('files').textContent);
    const subscriptions = JSON.parse(document.getElementById('subscriptions').textContent);

    const fileTree = new FileTree(paths, subscriptions);
    console.log(fileTree)

    let container = document.getElementById('file-tree-container');
    let dataBinder =  new DataBinder('file-tree', fileTree);
    container.addEventListener('click', dataBinder);
});