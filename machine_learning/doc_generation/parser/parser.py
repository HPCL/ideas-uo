import ply.yacc as yacc

from tokenizer import tokens

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

def p_expression(p):
    '''expression : word expression
                  | expression quantifier
                  | group expression
                  | number expression
                  | expression PIPE expression
                  | string expression
                  | anchor expression
                  | expression anchor
                  | character_class expression
                  | closure expression
                  | empty
    '''
    if len(p) == 3:
        p[0] = Node('Expression', children=[p[1], p[2]])
    elif len(p) == 4:
        p[0] = Node('Alternation', children=[p[1], p[3]], value='or')

def p_character_class(p):
    '''character_class : OPEN_BRACKETS character_expression CLOSE_BRACKETS
    '''

    p[0] = Node('CharacterClass', children=[p[2]])

def p_character_expression(p):
    '''character_expression : character_range character_expression
                            | anchor character_expression
                            | character_expression anchor
                            | integer character_expression
                            | UNDERSCORE character_expression
                            | empty
    '''
    if len(p) == 3:
        p[0] = Node('CharacterExpression', children=[p[1], p[2]])

    elif len(p) == 4:
        p[0] = Node('CharacterExpression', children=[p[2], p[3]])

def p_character_range(p):
    '''character_range : letter MINUS_SIGN letter
                       | digit MINUS_SIGN digit
    '''

    p[0] = Node('CharacterRange', value=p[1].type)

def p_quantifier(p):
    '''quantifier : PLUS_SIGN
                  | ASTERISK
                  | QUESTION_MARK
                  | OPEN_CURLYBRACES integer CLOSE_CURLYBRACES
                  | OPEN_CURLYBRACES integer COMMA CLOSE_CURLYBRACES
                  | OPEN_CURLYBRACES integer COMMA integer CLOSE_CURLYBRACES
                  | quantifier QUESTION_MARK
    '''

    if len(p) == 2:
        p[0] = Node('Quantifier', value=p[1])
    elif len(p) == 4:
        p[0] = Node('Quantifier', value=p[2])
    elif len(p) == 5:
        p[0] = Node('Quantifier', children=[p[2]], value=p[3])
    elif len(p) == 6:
        p[0] = Node('Quantifier', children=[p[2], p[4]], value=p[3])

def p_anchor(p):
    '''anchor : ANCHOR
              | DOLLAR_SIGN
              | CARET_SIGN
    '''

    p[0] = Node('Anchor', value=p[1])

def p_group(p):
    '''group : OPEN_PARENS expression CLOSE_PARENS
             | OPEN_NONCAPTURE_PARENS expression CLOSE_PARENS
             | OPEN_POSITIVE_LOOKAHEAD_PARENS expression CLOSE_PARENS
             | OPEN_NEGATIVE_LOOKAHEAD_PARENS expression CLOSE_PARENS
    '''
    values = {
        '(' : 'capture',
        '(?!' : 'negative lookahead',
        '(?=' : 'positive lookahead',
        '(?:' : 'non-capture'
    }

    value = values[p[1]]

    p[0] = Node('Group', children=[p[2]], value=value)

def p_closure(p):
    '''closure : OPEN_ANGLE expression CLOSE_ANGLE
               | OPEN_BRACKETS expression CLOSE_BRACKETS
               | OPEN_CURLYBRACES expression CLOSE_CURLYBRACES
    '''
    values = {
        '<' : 'angle',
        '[' : 'bracket',
        '{' : 'curly brace'
    }

    value = values[p[1]]

    p[0] = Node('Closure', children=[p[2]], value=value)

def p_number(p):
    '''number : NUMBER
    '''

    p[0] = Node('Number', value=p[1])

def p_integer(p):
    '''integer : digit integer
               | empty
    '''

    if len(p) == 3:
        p[0] = Node('Integer', children=[p[2]], value=p[1])

def p_digit(p):
    '''digit : "0"
             | "1"
             | "2"
             | "3"
             | "4"
             | "5"
             | "6"
             | "7"
             | "8"
             | "9"
    '''

    p[0] = Node('Digit', value=p[1])

def p_letter(p):
    '''letter : "a"
              | "b"
              | "c"
              | "d"
              | "e"
              | "f"
              | "g"
              | "h"
              | "i"
              | "j"
              | "k"
              | "l"
              | "m"
              | "n"
              | "o"
              | "p"
              | "q"
              | "r"
              | "s"
              | "t"
              | "u"
              | "v"
              | "w"
              | "x"
              | "y"
              | "z"
              | "A"
              | "B"
              | "C"
              | "D"
              | "E"
              | "F"
              | "G"
              | "H"
              | "I"
              | "J"
              | "K"
              | "L"
              | "M"
              | "N"
              | "O"
              | "P"
              | "Q"
              | "R"
              | "S"
              | "T"
              | "U"
              | "V"
              | "W"
              | "X"
              | "Y"
              | "Z"
    '''

    p[0] = Node('Letter', value=p[1])

def p_punctuation(p):
    '''punctuation : EXCLAMATION_MARK
                   | DOLLAR_SIGN
                   | AT_SIGN
                   | POUND_SIGN
                   | TILDE
                   | SINGLE_QUOTE
                   | OPEN_PARENS
                   | CLOSE_PARENS
                   | BACK_QUOTE
                   | PLUS_SIGN
                   | COMMA
                   | MINUS_SIGN
                   | PERIOD
                   | FORWARD_SLASH
                   | COLON
                   | SEMICOLON
                   | OPEN_ANGLE
                   | EQUALS
                   | CLOSE_ANGLE
                   | QUESTION_MARK
                   | CLOSE_BRACKETS
                   | DOUBLE_QUOTE
                   | OPEN_BRACKETS
                   | CARET_SIGN
                   | UNDERSCORE
                   | AMPERSAND
                   | OPEN_CURLYBRACES
                   | PIPE
                   | CLOSE_CURLYBRACES
                   | ASTERISK
                   | PERCENT_SIGN
                   | BACK_SLASH
    '''

    p[0] = Node('Punctuation', value=p[1])

def p_whitespace(p):
    '''whitespace : WHITESPACE_SEPARATOR
                  | TAB
                  | SPACE
    '''

    p[0] = Node('Whitespace', value=p[1])

def p_string(p):
    '''string : BACK_SLASH punctuation string
              | digit string
              | letter string
              | whitespace string
              | STRING
              | empty
    '''
    if len(p) == 3:
        p[0] = Node('String', children=[p[2]], value=p[1])
    elif len(p) == 2 and p[1]:
        p[0] = Node('String', value=p[1])
    elif len(p) == 4:
        p[0] = Node('String', children=[p[3]], value=p[2])

def p_word(p):
    '''word : WORD
    '''

    p[0] = Node('Word', value=p[1])

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
    s = '^author (.*)'
    s = '.*\.(a|so|dylib)$'
    s = '{(\w+)}'
    result = parser.parse(s, debug=log)
    print(result)
