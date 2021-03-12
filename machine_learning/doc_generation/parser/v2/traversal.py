from parser import parser, log, Node
from tokenizer import lexer

from collections import defaultdict
from random import choice

def postorderf(root):
    level = 1
    stack = [(root, level)]
    res = []

    while len(stack) > 0:
        node, level = stack.pop()
        res.insert(0, (node.type, node.value, level))

        for child in node.children:
            if child:
                stack.insert(0, (child, level + 1))

    return res


def postorder(root):

    traversal = []

    def postorder_helper(node, level):

        if not node:
            return

        traversal.append((node.type, node.value, level))

        for child in node.children:
            postorder_helper(child, level + 1)

    postorder_helper(root, 1)
    return traversal

def build_expressionf(traversal):
    paths = []
    path = []
    i = 0

    while True:
        j = i + 1
        if j == len(traversal):
            path.append(traversal[i])
            paths.append(path)
            return paths

        if traversal[j][2] < traversal[i][2]:
            path.append(traversal[i])
            paths.append(path)
            path = []
        elif traversal[j][2] > traversal[i][2]:
            path.append(traversal[i])

        i += 1
    return paths

def build_expression(traversal):
    paths = []
    path = []

    for curr, next in zip(traversal, traversal[1:] + [None]):
        path.append(curr)
        if not next or next[0] == 'Expression':
            paths.append(path)
            path = []

    return paths

def phrase(paths):
    sequence = []
    closure = False
    struct = False
    
    for path in paths:
        if all(e[0] == 'Structure' for e in path):
            priority = {
                'starting with': 1,
                'suffix': 2,
                'skip beginning': 0,
                None: -1
            }

            term = max([(e[1], priority[e[1]]) for e in path], key=lambda x: x[1])[0]
            struct = True

        elif all(e[0] in {'String', 'Letter', 'Digit', 'Punctuation'} for e in path[1:]):
            term = '"'
            for s in path[2::2]:
                if s[1] is None:
                    term += ''
                else:
                    term += s[1]
            term += '"'

        elif all(e[0] in {'String', 'Letter', 'Digit', 'Punctuation', 'Alternation'} for e in path[1:]):
            term = ''
            i = 1

            while path[i][0] == 'Alternation':
                i += 1

            prev = -1

            for s in path[i + 1::2]:
                if prev == -1:
                    term += '"'
                    
                if s[1] is None:
                    term += ''
                elif s[2] < prev:
                    term += '" or "'
                    term += s[1]
                    prev = s[2]
                else:
                    term += s[1]
                    prev = s[2]
             
            term += '"'

        elif path[1][0] == 'Anything':
            term = path[1][1]

        elif path[1][0] == 'CharacterClass':
            term = ''
            
            if 'negated' in path[1][1]:
                term += 'not one of the following '
            else:
                term += 'one of the following '

            i = 1
            while path[i][0] != 'Quantifier':
                i += 1
            
            zs = []
            prev = -1
            z = ''
            for s in path[i + 1:]:
                if s[2] <= prev:
                    zs.append(z[::-1])
                    prev = s[2]
                    z = ''
                    z += s[1].value
                else:
                    z += s[1].value
                    prev = s[2]

            zs.append(z[::-1])
            term += path[i][1].format(*zs) + ': '
            skip = 0
            
            for j, _ in enumerate(path[2:i]):
                if skip:
                    skip -= 1
                    continue
                    
                if path[2:i][j][0] == 'CharacterRange':
                    term += path[2:i][j][1].format(path[2:i][j+1][1], path[2:i][j+2][1])
                    skip = 2
                elif path[2:i][j][1]:
                    term += path[2:i][j][1]
                else:
                    #print('Unknown path:', path[2:i][j])
                    pass
               
                if path[2:i][j][1]:
                    term += ' '
                    
        elif path[1][0] == 'Closure':
            term = path[1][1]
            closure = True
            
        elif path[1][0] == 'Word':
            term = path[1][1]
            
        else:
            #print('Unknown path:', path)
            term = None
            
        if term:
            if closure and path[1][0] != 'Closure':
                closure = False
                sequence[-1] = term + ' ' + sequence[-1]
            elif struct and path[0][0] != 'Structure':
                struct = False
                if len(sequence):
                    sequence[-1] += ' ' + term
                else:
                    sequence.append(term)
            else:
                sequence.append(term)

    return sequence

def build_sequence(pattern):
    root = parser.parse(pattern, debug=log, lexer=lexer)
    traversal = postorder(root)
    paths = build_expression(traversal)
    sequence = phrase(paths)
    conjunctions = ['and', 'plus', 'followed by']
    sent = ''
    for token in sequence[:-1]:
        sent += token + ' ' + choice(conjunctions) + ' '
    sent += ' ' + sequence[-1]
    return sent

def parse_ast(pattern):
    root = parser.parse(pattern, debug=log, lexer=lexer)
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
