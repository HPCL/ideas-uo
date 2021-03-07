import ply.yacc as yacc

from tokenizer import tokens, lexer

class Node:
    def __init__(self, type, children=None, value=None):
        self.type = type
        if children:
            self.children = children
        else:
            self.children = []
        self.value = value

    def __repr__(self):
        return f'{self.type}({self.children}, {self.value})'

def p_pattern(p):
    '''pattern : SOL expression EOL
               | SOL CARET expression EOL
               | SOL expression BACK_SLASH
    '''

    if len(p) == 4:
        p[0] = Node('Pattern', children=[p[2]])
    elif len(p) == 5:
        p[0] = Node('Pattern', children=[p[3]], value='starting with')

def p_suffix(p):
    '''suffix : BACK_SLASH PERIOD expression DOLLAR_SIGN EOL
    '''

    p[0] = Node('Suffix', children=[p[3]], value='ending with')

def p_expression(p):
    '''expression : closure expression
                  | skip expression
                  | group expression
                  | word expression
                  | expression PIPE expression
                  | suffix expression
                  | string expression
                  | character_class expression
                  | anything
                  | empty
    '''

    if len(p) == 3:
        if p[1] == lexer.start:
            p[0] = Node('Expression', children=[p[2]])
        elif p[1] != lexer.end:
            p[0] = Node('Expression', children=[p[1], p[2]])
    elif len(p) == 4:
        p[0] = Node('Alternation', children=[p[1], p[3]], value='or')
    elif len(p) == 2:
        p[0] = Node('Expression', children=[p[1]])

def p_character_class(p):
    '''character_class : OPEN_BRACKET character_expression CLOSE_BRACKET
                       | OPEN_BRACKET character_expression CLOSE_BRACKET quantifier
    '''

    if len(p) == 4:
        p[0] = Node('Character_Class', children=[p[2]])
    elif len(p) == 5:
        p[0] = Node('Character_Class', children=[p[2], p[4]])

def p_character_expression(p):
    '''character_expression : character_range character_expression
                            | letter character_expression
                            | digit character_expression
                            | BACK_SLASH LOWERCASE_R character_expression
                            | empty
    '''

    if len(p) == 3:
        p[0] = Node('Character_Expression', children=[p[1], p[2]])

def p_character_range(p):
    '''character_range : letter HYPHEN letter
                       | digit HYPHEN digit
    '''

    if p[1].type == 'Letter':
        value = f'letters from {p[1].value} to {p[3].value}'
        p[0] = Node('Character_Range', value=value)
    elif p[1].type == 'Digit':
        value = f'numbers from {p[1].value} to {p[3].value}'
        p[0] = Node('Character_Range', value=value)

def p_quantifier(p):
    '''quantifier : OPEN_CURLYBRACE integer CLOSE_CURLYBRACE
                  | OPEN_CURLYBRACE integer COMMA CLOSE_CURLYBRACE
                  | OPEN_CURLYBRACE integer COMMA integer CLOSE_CURLYBRACE
                  | PLUS_SIGN
                  | ASTERISK
                  | QUESTION_MARK
    '''

    if len(p) == 4:
        p[0] = Node('Quantifier', value='exactly {} time(s)')
    elif len(p) == 5:
        p[0] = Node('Quantifier', value='at least {} time(s)')
    elif len(p) == 6:
        p[0] = Node('Quantifier', value='between {} and {} times')
    elif len(p) == 1:
        if p[1] == '+':
            p[0] = Node('Quantifier', value='at least once')
        elif p[1] == '*':
            p[0] = Node('Quantiifer', value='0 or more times')
        elif p[1] == '?':
            p[0] = Node('Quantiifer', value='fewest possible occurences')

def p_integer(p):
    '''integer : digit integer
               | empty
    '''

    if len(p) == 2:
        p[0] = Node('Integer', children=[p[2]], value=p[1])

def p_anything(p):
    '''anything : PERIOD ASTERISK
                | PERIOD PLUS_SIGN
    '''

    p[0] = Node('Anything')

def p_string(p):
    '''string : letter string
              | digit string
              | punctuation string
              | SPACE string
              | empty
    '''

    if len(p) == 3:
        p[0] = Node('String', children=[p[2]], value=p[1])

def p_punctuation(p):
    '''punctuation : BACK_SLASH EXCLAMATION_MARK
                   | DOUBLE_QUOTE
                   | HASHTAG
                   | BACK_SLASH DOLLAR_SIGN
                   | PERCENT_SIGN
                   | AMPERSAND
                   | SINGLE_QUOTE
                   | BACK_SLASH OPEN_PAREN
                   | BACK_SLASH CLOSE_PAREN
                   | BACK_SLASH ASTERISK
                   | BACK_SLASH PLUS_SIGN
                   | COMMA
                   | HYPHEN
                   | BACK_SLASH PERIOD
                   | FORWARD_SLASH
                   | COLON
                   | SEMICOLON
                   | OPEN_ANGLE
                   | CLOSE_ANGLE
                   | EQUAL_SIGN
                   | BACK_SLASH QUESTION_MARK
                   | AT_SIGN
                   | BACK_SLASH OPEN_BRACKET
                   | BACK_SLASH BACK_SLASH
                   | BACK_SLASH CLOSE_BRACKET
                   | BACK_SLASH CARET
                   | UNDERSCORE
                   | BACKTICK
                   | BACK_SLASH OPEN_CURLYBRACE
                   | BACK_SLASH PIPE
                   | BACK_SLASH CLOSE_CURLYBRACE
                   | TILDE
    '''
    if len(p) == 2:
        p[0] = Node('Punctuation', value=p[1])
    elif len(p) == 3:
        p[0] = Node('Punctuation', value=p[2])

def p_letter(p):
    '''letter : LOWERCASE_A
              | LOWERCASE_B
              | LOWERCASE_C
              | LOWERCASE_D
              | LOWERCASE_E
              | LOWERCASE_F
              | LOWERCASE_G
              | LOWERCASE_H
              | LOWERCASE_I
              | LOWERCASE_J
              | LOWERCASE_K
              | LOWERCASE_L
              | LOWERCASE_M
              | LOWERCASE_N
              | LOWERCASE_O
              | LOWERCASE_P
              | LOWERCASE_Q
              | LOWERCASE_R
              | LOWERCASE_S
              | LOWERCASE_T
              | LOWERCASE_U
              | LOWERCASE_V
              | LOWERCASE_W
              | LOWERCASE_X
              | LOWERCASE_Y
              | LOWERCASE_Z
              | UPPERCASE_A
              | UPPERCASE_B
              | UPPERCASE_C
              | UPPERCASE_D
              | UPPERCASE_E
              | UPPERCASE_F
              | UPPERCASE_G
              | UPPERCASE_H
              | UPPERCASE_I
              | UPPERCASE_J
              | UPPERCASE_K
              | UPPERCASE_L
              | UPPERCASE_M
              | UPPERCASE_N
              | UPPERCASE_O
              | UPPERCASE_P
              | UPPERCASE_Q
              | UPPERCASE_R
              | UPPERCASE_S
              | UPPERCASE_T
              | UPPERCASE_U
              | UPPERCASE_V
              | UPPERCASE_W
              | UPPERCASE_X
              | UPPERCASE_Y
              | UPPERCASE_Z
    '''
    p[0] = Node('Letter', value=p[1])

def p_digit(p):
    '''digit : DIGIT_0
             | DIGIT_1
             | DIGIT_2
             | DIGIT_3
             | DIGIT_4
             | DIGIT_5
             | DIGIT_6
             | DIGIT_7
             | DIGIT_8
             | DIGIT_9
    '''

    p[0] = Node('Digit', value=p[1])


def p_skip(p):
    '''skip : SOL anything
    '''

    p[0] = Node('Skip')

def p_group(p):
    '''group : OPEN_PAREN expression CLOSE_PAREN
    '''

    if len(p) == 4:
        p[0] = Node('Group', children=[p[2]], value='capture')

def p_closure(p):
    '''closure : OPEN_CURLYBRACE expression CLOSE_CURLYBRACE
               | BACK_SLASH OPEN_BRACKET expression BACK_SLASH CLOSE_BRACKET
               | OPEN_ANGLE expression CLOSE_ANGLE
    '''

    symbol = {
        '{': 'curly braces',
        '[': 'brackets',
        '<': 'angles',
        '(': 'parantheses'
    }

    if len(p) == 4:
        sym = symbol[p[1]]
        p[0] = Node('Closure', children=[p[2]], value=f'enclosed by {sym}')

def p_word(p):
    '''word : BACK_SLASH LOWERCASE_W PLUS_SIGN
            | BACK_SLASH LOWERCASE_W ASTERISK
    '''

    p[0] = Node('Word')

def p_empty(p):
    '''empty : '''

    pass

def p_error(p):
    if p:
         print("Syntax error at token", p.type)
         # Just discard the token and tell the parser it's okay.
         parser.errok()
    else:
         print("Syntax error at EOF")

# Set up a logging object
import logging
logging.basicConfig(
    level = logging.DEBUG,
    filename = "parselog.txt",
    filemode = "w",
    format = "%(filename)10s:%(lineno)4d:%(message)s"
)
log = logging.getLogger()

parser = yacc.yacc(debug=True, debuglog=log)

if __name__ == '__main__':
    s = 'Content-Type:[^\r\n]+'
    s = '^author (.*)'
    #s = '.*\.(a|so|dylib)$'
    #s = '{(\w+)}'
    #s = '\.'
    print(s)
    result = parser.parse(s, debug=log, lexer=lexer)
    print(result)
