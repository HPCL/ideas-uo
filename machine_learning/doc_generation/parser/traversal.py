from parser import parser, log

def preorder(root):
    if not root: return

    stack = []
    level = 0
    stack.append((root, level))

    while len(stack) > 0:
        node, level = stack.pop()
        print(' '*level + f'{node.type}({node.value})')

        for child in node.children[::-1]:
            if child:
                stack.append((child,level+1))

def viewtree(pattern):
    print('-'*80)
    print(f'Pattern: {pattern}')
    root = parser.parse(pattern, debug=log)
    print('='*80)
    print(f'Parsed: {root}')
    print('='*80)
    preorder(root)
    print('-'*80)

#viewtree('{(\w+)}')
#viewtree('^author (.*)')
#viewtree('.*\.(a|so|dylib)$')
