from parser import parser, log, Node

from collections import defaultdict

def postorder(root):
    stack = []
    res = []
    level = 1
    stack.append((root, level))

    while len(stack) > 0:
        node, level = stack.pop()
        res.insert(0, (node.type, node.value, level))
        for child in node.children:
            if child:
                stack.append((child, level+1))

    return res

def build_expression(traversal):
    paths = []
    path = []
    i = 0

    while True:
        j = i + 1
        if j == len(traversal):
            path.append(traversal[i])
            paths.append(path)
            return paths

        if traversal[j][2] > traversal[i][2]:
            path.append(traversal[i])
            paths.append(path)
            path = []
        elif traversal[j][2] < traversal[i][2]:
            path.append(traversal[i])

        i += 1
    return paths

def parse_ast(pattern):
    root = parser.parse(pattern, debug=log)
    traversal = postorder(root)
    paths = build_expression(traversal)
    return paths

def process_ast(paths):
    subtrees = defaultdict(list)

    def process_string(path):
        string = ''
        _, _, level = path[-1]
        for _, value, _ in path[::-1]:
            string += value.value
        return string, level

    stack = []
    for path in paths:
        stack.insert(0, path)

    while len(stack) > 0:
        path = stack.pop()

        # Check for leaf nodes
        if len(path) == 1:
            expr, value, level = path[0]

            # Anchor tag string value
            if expr == 'Anchor':
                if value == '$':
                    subtrees[level].append('end of line')
                elif value == '^':
                    subtrees[level].append('start of line')
            # String tag inner value
            elif expr == 'String':
                if isinstance(value, Node):
                    subtrees[level].append(f'{value.type.lower()} "{value.value}"')
                else:
                    if value == '.*':
                        subtrees[level].append('anything')
            elif expr == 'Word':
                subtrees[level].append('word')
            elif expr == 'Alternation':
                subtrees[level].append('or')
            elif expr == 'Expression':
                subtrees[level].append('EXPR')
            elif expr == 'Closure':
                subtrees[level].append(f'enclosed by {value}')
        else:
            exprs = list(set(node[0] for node in path))
            # If all nodes on a path are the same type
            if len(exprs) == 1:
                # Concatenate string nodes into single string
                if exprs[0] == 'String':
                    string, level = process_string(path)
                    subtrees[level].append(f'string "{string}"')
            else:
                result = ''
                start = 0
                end = 0
                for i, (curr, next) in enumerate(zip(path, path[1:])):
                    if curr[0] == 'Expression' or curr[0] != next[0]:
                        end = i + 1
                        stack.insert(0, path[start:end])
                        start = i + 1

    return subtrees

def translate_ast(paths):
    subtrees = process_ast(paths)

    for key in sorted(subtrees.keys(), reverse=True):
        j = 1
        while key - j > 0 and key - j not in subtrees.keys():
            j += 1

        if 'EXPR' in subtrees[key - j]:
            i = subtrees[key - j].index('EXPR')
            subtrees[key - j][i] = ' '.join(subtrees[key])
        else:
            if any('enclosed by' in obj for obj in subtrees[key - j]):
                for i, obj in enumerate(subtrees[key - j]):
                    if 'enclosed by' in obj:
                        subtrees[key - j].insert(i, ' '.join(subtrees[key]))
                        break
            else:
                subtrees[key - j].append(' '.join(subtrees[key]))

    sequence = subtrees[0]

    return sequence
