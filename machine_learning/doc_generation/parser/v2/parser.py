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

    def __hash__(self):
        return hash(str(self))

def p_structure(p):
    '''structure : SOL structure
                 | SOL CARET structure
                 | SOL anything structure
                 | BACK_SLASH PERIOD structure DOLLAR_SIGN EOL
                 | expression structure
                 | expression
                 | EOL
    '''
    if len(p) == 2:
        if p[1] != lexer.end:
            p[0] = Node('Structure', children=[p[1]])
    elif len(p) == 3:
        if p[1] == lexer.start:
            p[0] = Node('Structure', children=[p[2]])
        else:
            p[0] = Node('Structure', children=[p[1], p[2]])
    elif len(p) == 4:
        if p[2] == '^':
            p[0] = Node('Structure', children=[p[3]], value='starting with')
        else:
            p[0] = Node('Structure', children=[p[3]], value='skip beginning')
    elif len(p) == 6:
        p[0] = Node('Structure', children=[p[3]], value='suffix')

def p_expression(p):
    '''expression : string expression
                  | anything expression
                  | group expression
                  | closure expression
                  | word expression
                  | alternation expression
                  | character_class expression
                  | string
                  | anything
                  | group
                  | closure
                  | word
                  | alternation
                  | character_class
    '''

    if len(p) == 2:
        p[0] = Node('Expression', children=[p[1]])
    elif len(p) == 3:
        p[0] = Node('Expression', children=[p[1], p[2]])

def p_character_class(p):
    '''character_class : OPEN_BRACKET character_expression CLOSE_BRACKET
                       | OPEN_BRACKET CARET character_expression CLOSE_BRACKET
                       | OPEN_BRACKET character_expression CLOSE_BRACKET quantifier
                       | OPEN_BRACKET CARET character_expression CLOSE_BRACKET quantifier
    '''

    if len(p) == 4:
        p[0] = Node('CharacterClass', children=[p[2]])
    elif len(p) == 5:
        if p[2] == '^':
            p[0] = Node('CharacterClass', children=[p[3]], value='negated set')
        else:
            p[0] = Node('CharacterClass', children=[p[2], p[4]], value='quantified set')
    elif len(p) == 6:
        p[0] = Node('CharacterClass', children=[p[3], p[5]], value='quantified negated set')

def p_character_expression(p):
    '''character_expression : escape_character character_expression
                            | letter character_expression
                            | digit character_expression
                            | character_range character_expression
                            | punctuation character_expression
                            | escape_character
                            | letter
                            | digit
                            | character_range
                            | punctuation
    '''

    if len(p) == 2:
        p[0] = Node('CharacterExpression', children=[p[1]])
    elif len(p) == 3:
        p[0] = Node('CharacterExpression', children=[p[1], p[2]])

def p_character_range(p):
    '''character_range : letter HYPHEN letter
                       | digit HYPHEN digit
    '''

    if p[1].type == 'Letter':
        p[0] = Node('CharacterRange', children=[p[1], p[3]], value='letters from {} to {}')
    else:
        p[0] = Node('CharacterRange', children=[p[1], p[3]], value='numbers from {} to {}')

def p_escape_character(p):
    '''escape_character : BACK_SLASH letter
    '''

    p[0] = Node('EscapeCharacter', children=[p[2]])

def p_quantifier(p):
    '''quantifier : OPEN_CURLYBRACE integer CLOSE_CURLYBRACE
                  | OPEN_CURLYBRACE integer COMMA CLOSE_CURLYBRACE
                  | OPEN_CURLYBRACE integer COMMA integer CLOSE_CURLYBRACE
                  | PLUS_SIGN
                  | ASTERISK
                  | QUESTION_MARK
    '''

    if len(p) == 2:
        if p[1] == '+':
            p[0] = Node('Quantifier', value='at least once')
        elif p[1] == '*':
            p[0] = Node('Quantifier', value='0 or more times')
        elif p[1] == '?':
            p[0] = Node('Quantifier', value='fewest possible occurences')
    elif len(p) == 4:
        p[0] = Node('Quantifier', children=[p[2]], value='exactly {} time(s)')
    elif len(p) == 5:
        p[0] = Node('Quantifier', children=[p[2]], value='at least {} time(s)')
    elif len(p) == 6:
        p[0] = Node('Quantifier', children=[p[2], p[4]], value='between {} and {} times')

def p_integer(p):
    '''integer : integer digit
               | digit
    '''

    if len(p) == 2:
        p[0] = Node('Integer', value=p[1])
    elif len(p) == 3:
        p[0] = Node('Integer', children=[p[1]], value=p[2])

def p_alternation(p):
    '''alternation : alternation PIPE string
                   | string
    '''

    if len(p) == 2:
        p[0] = Node('Alternation', children=[p[1]], value='or')
    elif len(p) == 4:
        p[0] = Node('Alternation', children=[p[1], p[3]], value='or')

def p_word(p):
    '''word : BACK_SLASH LOWERCASE_W PLUS_SIGN
            | BACK_SLASH LOWERCASE_W ASTERISK
    '''

    p[0] = Node('Word', value ='a word')

def p_closure(p):
    '''closure : OPEN_CURLYBRACE group CLOSE_CURLYBRACE
               | OPEN_ANGLE group CLOSE_ANGLE
               | BACK_SLASH OPEN_BRACKET group BACK_SLASH CLOSE_BRACKET
               | BACK_SLASH OPEN_PAREN group BACK_SLASH CLOSE_PAREN
    '''

    if len(p) == 4:
        if p[1] == '{':
            p[0] = Node('Closure', children=[p[2]], value='enclosed by curly braces')
        else:
            p[0] = Node('Closure', children=[p[2]], value='enclosed by angles')
    elif len(p) == 6:
        if p[2] == '[':
            p[0] = Node('Closure', children[p[3]], value='enclosed by brackets')
        else:
            p[0] = Node('Closure', children[p[3]], value='enclosed by parentheses')


def p_group(p):
    '''group : OPEN_PAREN expression CLOSE_PAREN
             | group quantifier
    '''
    if len(p) == 3:
        p[0] = Node('Group', children=[p[1], p[2]], value='quantified group')
    elif len(p) == 4:
        p[0] = Node('Group', children=[p[2]], value='capture group')

def p_anything(p):
    '''anything : PERIOD ASTERISK
                | PERIOD PLUS_SIGN
    '''

    p[0] = Node('Anything', value='anything')

def p_string(p):
    '''string : letter string
              | digit string
              | punctuation string
              | letter
              | digit
              | punctuation
    '''

    if len(p) == 2:
        p[0] = Node('String', children=[p[1]])
    elif len(p) == 3:
        p[0] = Node('String', children=[p[1], p[2]])

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
                   | OPEN_CURLYBRACE
                   | BACK_SLASH PIPE
                   | CLOSE_CURLYBRACE
                   | TILDE
                   | SPACE
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
    s = r'Content-Type:[^\r\n]+'
    #s = '^author (.*)'
    #s = '.*\.(a|so|dylib)$'
    #s = '{(\w+)}'
    #s = 'm(0){2,}'
    s = r'\[-(.)\]'
    print(s)
    result = parser.parse(s, debug=log, lexer=lexer)
    print(result)
