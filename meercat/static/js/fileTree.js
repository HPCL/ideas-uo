const SEPARATOR = '/';

// All paths, relative or absolute, start and end without a slash
class Path {

    // Returns an string with the common prefix of both paths.
    static commonPrefix(path1, path2) {
        let i = 0;
        while (i < path1.length && i < path2.length && path1[i] === path2[i]) {
            i += 1;
        }

        return path1.slice(0, i - 1 < 0 ? 0 : i - 1);
    }

    // returns the string difference between path and subpath.
    static trailingPath(path, subPath) {
        if (!subPath || !path.includes(SEPARATOR) || !path.includes(subPath)) return path;

        return path.slice(subPath.length + 1);
    }

    // Returns last component in this.path. Returns an empty string if path is empty.
    static baseName(path) {
        let crumbs = path.split(SEPARATOR);
        let tail = crumbs.pop();
        return tail;
    }

    // Returns a list with every component in the path
    static crumbs(path) {
        return path.split(SEPARATOR);
    }

    // Returns joint paths
    static join(path1, path2) {
        if (path1 === '') return path2;
        if (path2 === '') return path1;

        return [path1, path2].join(SEPARATOR);
    }
}

class TreeNode {
    constructor({ parent, path, metrics}) {
        this.metrics = metrics? 
        metrics
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
        this.children = [];
        this.subscribed = false;
        this.visible = true;
    }

    // path should be relative to project root
    getChild(path) {
        for (let child of this.children) {
            if (child.path === path) {
                return child;
            }
        }

        return null;
    }

    hasChild(path) {
        return this.children.some(child => child.path === path);
    }

    // The path should be relative to the project root
    getDescendant(path) {
        let commonPrefix = Path.commonPrefix(this.path, path);
        let trailingPath = Path.trailingPath(path, commonPrefix);

        const trailingCrumbs = Path.crumbs(trailingPath);
        let currentPath = commonPrefix;
        let descendant = this;
        for (let crumb of trailingCrumbs) {
            currentPath = Path.join(currentPath, crumb);
            descendant = descendant.getChild(currentPath);

            if (descendant === null) break;
        }

        return descendant;
    }

    addChildNode(node) {
        this.children.push(node);
    }

    isLeaf() {
        return this.children.length === 0;
    }

    // This function adds a child Node with the subtree built from path.
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

    updateParentSubscriptions() {
        // 
        if (this.parent === null) return;
        const SubscribedSiblingCount = this.parent.children.reduce((count, child) => child.subscribed? count + 1 : count, 0);
        const nullSiblingCount = this.parent.children.reduce((count, child) => child.subscribed === null? count + 1: count, 0);
        const siblingCount = this.parent.children.length;

        if (nullSiblingCount > 0) {
            this.parent.subscribed = null;
        } else if (SubscribedSiblingCount === siblingCount) {
            this.parent.subscribed = true;
        } else if (SubscribedSiblingCount === 0) {
            this.parent.subscribed = false;
        } else {
            this.parent.subscribed = null;
        }

        if (this.parent !== null) {
            this.parent.updateParentSubscriptions();
        }
    }

    updateSubtreeSubscriptions() {
        /**
         * updateSubtreeSubscriptions: changes the subscription based on the current subscription value for "this".
         */
        
        // Terminology: Files for which the user is notified on pull requests are called subscriptions
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

    updateSubscriptions() {
        this.updateSubtreeSubscriptions();
        this.updateParentSubscriptions();
    }

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

    getSubscribedNodePaths() {
        let subscribedNodePaths = [];
        for (let node in this) {
            if (node.isLeaf() && node.subscribed) subscribedNodePaths.push(node.path);
        }
        return subscribedNodePaths;
    }

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
            this.metrics.documentation.missingDocs += child.metrics.documentation.missingDocs;
            this.metrics.documentation.nonDoxyDocs += child.metrics.documentation.nonDoxyDocs;
            this.metrics.busFactor += child.metrics.busFactor;
            this.metrics.linter += child.metrics.linter;
        }

        this.visible = visible;
        if (childrenWithMetrics === 0) return;
        this.metrics.documentation.total = Math.round(this.metrics.documentation.total / childrenWithMetrics);
        this.metrics.documentation.missingDocs = Math.round(this.metrics.documentation.missingDocs / childrenWithMetrics);
        this.metrics.documentation.nonDoxyDocs = Math.round(this.metrics.documentation.nonDoxyDocs / childrenWithMetrics);
        this.metrics.busFactor = Math.round(this.metrics.busFactor / childrenWithMetrics);
        this.metrics.linter = Math.round(this.metrics.linter / childrenWithMetrics);
    }
}

class FileTreeLi {
    static createIcon(src, alt, classList) {
        const icon = document.createElement('img');
        icon.src = src;
        icon.alt = alt;

        icon.classList.add(...classList);

        return icon;
    }

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

    static render(treeNode) {

        const wrapper = document.createElement('div');

        const nodeLabel = document.createElement('span');
        if (treeNode.visible) nodeLabel.classList.add(['node-label']);
        nodeLabel.textContent = treeNode.label;

        let icons;
        if (!treeNode.visible) {
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

        let subscriptionSrc = treeNode.subscribed ? '/static/images/subscription-icon.png' : (treeNode.subscribed === null ? '/static/images/partial-subscription-icon.png' : '');
        let subscriptionAlt = treeNode.subscribed ? 'You will get notifications on pull requests' : (treeNode.subscribed === null ? 'You will get notifications for some iems under this folder on pull requests' : '');
        let subscriptionIcon = FileTreeLi.createIcon(subscriptionSrc, subscriptionAlt, ['post-label-icon']);
        subscriptionIcon.classList.add('subscription-icon');
        subscriptionIcon.onerror = function () { this.style.display = 'none'; };

        wrapper.append(...icons, nodeLabel, subscriptionIcon);

        return wrapper;
    }
}

class Renderer {
    static createTreeNode(treeNode) {
        return FileTreeLi.render(treeNode);
    }

    static renderPanel(treeNode) {

        const documentationBar = document.getElementById('documentation-bar');
        const documentationMetric = document.getElementById('documentation-metric');

        const missingDocsBar = document.getElementById('missing-docs-bar');
        const missingDocsMetric = document.getElementById('missing-docs-metric');
        const nonDoxyDocsBar = document.getElementById('non-doxy-docs-bar');
        const nonDoxyDocsMetric = document.getElementById('non-doxy-docs-metric');

        // const busFactorBar = document.getElementById('bus-factor-bar');
        // const busFactorMetric = document.getElementById('bus-factor-metric');
        const linterBar = document.getElementById('linter-bar');
        const linterMetric = document.getElementById('linter-metric');

        documentationBar.style.width = treeNode.metrics.documentation.total + '%';
        documentationBar.className = `error-${Math.floor(treeNode.metrics.documentation.total * 3 / 101)}`;

        missingDocsBar.style.width = treeNode.metrics.documentation.missing + '%';
        missingDocsBar.className = `error-${Math.floor(treeNode.metrics.documentation.missing * 3 / 101)}`;
        nonDoxyDocsBar.style.width = treeNode.metrics.documentation.issues + '%';
        nonDoxyDocsBar.className = `error-${Math.floor(treeNode.metrics.documentation.issues * 3 / 101)}`;

        documentationMetric.textContent = treeNode.metrics.documentation.total;
        missingDocsMetric.textContent = treeNode.metrics.documentation.missing;
        nonDoxyDocsMetric.textContent = treeNode.metrics.documentation.issues;

        // busFactorBar.style.width = treeNode.metrics.busFactor + '%';
        // busFactorBar.className = `error-${Math.floor(treeNode.metrics.busFactor * 3 / 101)}`;
        // busFactorMetric.textContent = treeNode.metrics.busFactor;
        linterBar.style.width = treeNode.metrics.linter + '%';
        linterBar.className = `error-${Math.floor(treeNode.metrics.linter * 3 / 101)}`;
        linterMetric.textContent = treeNode.metrics.linter;

        const fileLabel = document.getElementById('path');
        fileLabel.textContent = treeNode.path;
        document.getElementById('hyperlink-icon').style.visibility = 'visible';

        const button = document.getElementById('panel-subscribe-btn');
        button.textContent = !treeNode.subscribed ? 'Notify on pull request' : 'Stop notifications';
        button.dataset.path = treeNode.path;
    }

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

    static updateSubscirptionIcon(treeNode) {
        let subscriptionIcon = document.querySelector('[data-path="' + treeNode.path + '"] > .rendered-element > .subscription-icon');
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

    static updateDOMParentSubscriptions(treeNode) {
        if (treeNode.parent === null) return;
        Renderer.updateSubscirptionIcon(treeNode.parent);
        Renderer.updateDOMParentSubscriptions(treeNode.parent);
    }

    static UpdateDOMSubtreeSubscriptions(treeNode) {
        for (let node of treeNode) {
            Renderer.updateSubscirptionIcon(node);
        }
    }
}

class DataBinder {
    constructor(elementId, fileTree) {
        this.fileTree = fileTree;
        Renderer.renderRoot(fileTree.root, elementId);
    }

    handleEvent(event) {
        if (event.type === 'click') {
            if (event.target.classList.contains(['switcher'])) {
                this.handleSwitcherClick(event);
            }

            if (event.target.classList.contains(['node-label'])) {
                this.handleNodeLabelClick(event);
            }

            if (event.target.id === 'panel-subscribe-btn') {
                this.handleSubscriptionClick(event);
            }
        }
    }

    handleNodeLabelClick(event) {
        const liNode = event.target.closest('li');
        const liTreeNode = this.fileTree.root.getDescendant(liNode.dataset.path);

        if (!liTreeNode.visible) return;

        Renderer.renderPanel(liTreeNode);

        const button = document.getElementById('panel-subscribe-btn');
        button.style = 'visibility: visible;';
    }

    handleSwitcherClick(event) {
        const liNode = event.target.closest('li');
        const liTreeNode = this.fileTree.root.getDescendant(liNode.dataset.path);
        const liNodeList = liNode.querySelector('ul');
        const parentList = liNode.closest('ul');
        const switcher = event.target;

        if (liNodeList.dataset.collapsed === 'false') {
            Renderer.collapseSection(liNodeList);
            Renderer.renderChildren(liNode, liTreeNode);
        } else {
            const expandedSiblingLiNodeList = parentList.querySelector('li > ul[data-collapsed="false"]');
            if (expandedSiblingLiNodeList !== null) {
                const expandedSiblingLiNode = expandedSiblingLiNodeList.closest('li');
                const expandedSiblingTreeNode = this.fileTree.root.getDescendant(expandedSiblingLiNode.dataset.path);
                Renderer.collapseSection(expandedSiblingLiNodeList);
                Renderer.renderChildren(expandedSiblingLiNode, expandedSiblingTreeNode);

                const switchers = expandedSiblingLiNode.querySelectorAll('span.switcher.expanded');
                switchers.forEach(switcher => switcher.classList.remove('expanded'));
            }

            Renderer.expandSection(liNodeList);
            for (let child of liTreeNode.children) {
                let childNode = document.querySelector('[data-path="' + child.path + '"]');
                Renderer.renderChildren(childNode, child);
            }
        }

        switcher.classList.toggle('expanded');
    }

    handleSubscriptionClick(event) {
        const treeNode = this.fileTree.root.getDescendant(event.target.dataset.path);

        // save current subscriptions in case of save failure
        const old_subscriptions = Array.from(this.fileTree.subscriptions); // make a copy of old subscriptions

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

        let subscriptions = JSON.stringify(Array.from(this.fileTree.subscriptions));
        const status = document.getElementById("save-status");
        status.innerText = "Loading..."
        event.target.disabled = true;

        $.ajax({
            url: '/dashboard/save_subscriptions/', 
            type: 'POST', 
            data: { subscriptions: subscriptions }, 
            success: (result) => {
                if (result.success === "true") {
                    event.target.textContent = !treeNode.subscribed ? 'Notify on pull request' : 'Stop notifications';
                    status.innerText = "notifications updated";

                    Renderer.UpdateDOMSubtreeSubscriptions(treeNode);
                    Renderer.updateDOMParentSubscriptions(treeNode);
                } else {
                    this.fileTree.subscriptions = old_subscriptions; // restore subscriptions on failure
                    status.innerText = "There was an error saving your notifications";
                    console.error(result.message);
                }
                event.target.disabled = false;
            },
            error: (error) => {
                this.fileTree.subscriptions = old_subscriptions; // restore subscriptions on failure

                status.innerText = "There was an error saving your notifications";
                console.error(error);
                event.target.disabled = false;
            } 
        });
    }
}

class FileTree {
    constructor(paths, subscriptions = []) {
        this.paths = paths;
        this.subscriptions = new Set(subscriptions);
        this.root = this.generateTreeWithMetrics(paths, this.subscriptions);
    }

    // This method injects dummy metrics, should be deleted when incorporating real metrics
    generateTreeWithMetrics(paths, subscriptions) {
        function randInt(min, max) {
            return Math.floor(Math.random() * (max - min + 1)) + min;
        }

        const tree = new TreeNode({ parent: null, path: ''});
    
        for (let path of paths) {
            let insertNode = tree.getDeepestMatchingNode(path);
            const trailingPath = Path.trailingPath(path, insertNode.path);
            let missing = randInt(0, 50);
            let issues = randInt(0, 50);
            if (path.endsWith('.F90')) {
                let metrics = path.endsWith('.F90')? { documentation: { total: missing + issues, missing, issues }, busFactor: randInt(0, 100), linter: randInt(0, 100) }: null;
                insertNode.insert(trailingPath, metrics);
            } else {
                insertNode.insert(trailingPath)
            }
        }

        for (let path of paths) {  
            if (subscriptions.has(path)) {
                tree.getDescendant(path).updateSubscriptions();

            }
        }

        tree.computeMetrics();

        return tree;
    }

}

$(document).ready(function() {

    const paths = JSON.parse(document.getElementById('files').textContent);
    const subscriptions = JSON.parse(document.getElementById('subscriptions').textContent);

    const fileTree = new FileTree(paths, subscriptions);
    
    let container = document.getElementById('file-tree-container');
    let dataBinder =  new DataBinder('file-tree', fileTree);
    container.addEventListener('click', dataBinder);
});