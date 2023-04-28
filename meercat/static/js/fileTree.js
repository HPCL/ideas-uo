const SEPARATOR = '/';

// All paths, relative or absolute, start and end without a slash
class Path {

    // Returns an string with the common prefix of both paths.
    static commonPrefix(path1, path2) {
        let i = 0;
        while (i < path1.length && i < path2.length && path1[i] === path2[i]) {
            console.log(i, path1[i], path2[i]);
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
    constructor({ parent, path, metrics }) {
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
        if (this.parent === null) return;
        const SubscribedSiblingCount = this.parent.children.reduce((count, child) => child.subscribed? count + 1 : count, 0);
        const nullSiblingCount = this.parent.children.reduce((count, child) => child.subscribed === null? count + 1: count, 0);
        const siblingCount = this.parent.children.length;

        console.log(this.parent.path, siblingCount, nullSiblingCount, SubscribedSiblingCount);
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
        if (!this.subscribed && this.subscribed !== null) {
            for (let node of this) {
                node.subscribed = true && node.visible;
            }
            return;
        }

        if (this.subscribed === null) {
            let confirmed = confirm("subcribing to this folder will unsubscribe from every file and folder underneath it. Continue?");
            if (!confirmed) return;
        }

        for (let node of this) {
            node.subscribed = false;
        }
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
        let subscriptionAlt = treeNode.subscribed ? 'Your are subscribed to this' : (treeNode.subscribed === null ? 'Some items under this folder have a subscription' : '');
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
            subscriptionIcon.alt = 'Some items under this folder have a subscription';
            subscriptionIcon.title = 'Some items under this folder have a subscription';
            subscriptionIcon.style.display = 'inline-block';
        } else if (treeNode.subscribed === true) {
            subscriptionIcon.src = '/static/images/subscription-icon.png';
            subscriptionIcon.alt = 'Your are subscribed to this';
            subscriptionIcon.title = 'Your are subscribed to this';
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
    constructor(elementId, tree) {
        this.tree = tree;
        Renderer.renderRoot(tree, elementId);
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
        const liTreeNode = this.tree.getDescendant(liNode.dataset.path);

        if (!liTreeNode.visible) return;

        Renderer.renderPanel(liTreeNode);

        const button = document.getElementById('panel-subscribe-btn');
        button.style = 'visibility: visible;';
    }

    handleSwitcherClick(event) {
        const liNode = event.target.closest('li');
        const liTreeNode = this.tree.getDescendant(liNode.dataset.path);
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
                const expandedSiblingTreeNode = this.tree.getDescendant(expandedSiblingLiNode.dataset.path);
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
        const treeNode = this.tree.getDescendant(event.target.dataset.path);

        treeNode.updateSubtreeSubscriptions();
        treeNode.updateParentSubscriptions();
        Renderer.UpdateDOMSubtreeSubscriptions(treeNode);
        Renderer.updateDOMParentSubscriptions(treeNode);

        event.target.textContent = !treeNode.subscribed ? 'Notify on pull request' : 'Stop notifications';
    }
}

class FileTree {
    constructor(paths, watchedPaths = []) {
        this.paths = paths;
        this.watchedPaths = new Set(watchedPaths);
        this.tree = this.generateTreeWithMetrics(paths);
        let container = document.getElementById('file-tree-container');
        let dataBinder =  new DataBinder('file-tree', this.tree);
        container.addEventListener('click', dataBinder);
    }

    getWatchedPaths() {
        return Array.from(this.watchedPaths);
    }

    // This method injects dummy metrics, should be deleted when incorporating real metrics
    generateTreeWithMetrics(paths) {
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

        tree.computeMetrics();

        return tree;
    }

}

$(document).ready(function() {

    const paths = JSON.parse(document.getElementById('files').textContent);

    const fileTree = new FileTree(paths);
    console.log(fileTree);
})