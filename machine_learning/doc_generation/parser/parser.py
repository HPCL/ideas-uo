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
                  | closure expression
                  | group expression
                  | number expression
                  | expression "|" expression
                  | string expression
                  | empty
    '''
    if len(p) == 3:
        p[0] = Node('Expression', children=[p[1], p[2]])
    elif len(p) == 2:
        p[0] = Node('Expression', children=[p[1]])
    elif len(p) == 4:
        p[0] = Node('Alternation', children=[p[1], p[3]], value='or')

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
              | digit number
              | empty
    '''
    if len(p) == 2:
        p[0] = Node('Number', value=p[1])
    elif len(p) == 3:
        p[0] = Node('Number', children=[p[2]], value=p[1])

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
    '''punctuation : "!"
                   | "#"
                   | "$"
                   | "%"
                   | "&"
                   | SINGLE_QUOTE
                   | OPEN_PARENS
                   | CLOSE_PARENS
                   | "*"
                   | "+"
                   | ","
                   | "-"
                   | "."
                   | "/"
                   | ":"
                   | ";"
                   | "<"
                   | "="
                   | ">"
                   | "?"
                   | "@"
                   | CLOSE_BRACKETS
                   | DOUBLE_QUOTE
                   | OPEN_BRACKETS
                   | "^"
                   | "_"
                   | "`"
                   | OPEN_CURLYBRACES
                   | "|"
                   | CLOSE_CURLYBRACES
                   | "~"
    '''

    p[0] = Node('Punctuation', value=p[1])

def p_word(p):
    '''word : WORD
            | letter word
            | digit word
            | empty
    '''

    if len(p) == 3:
        p[0] = Node('Word', children=[p[1]], value=p[2])
    elif len(p) == 2:
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

s = '*'
result = parser.parse(s, debug=log)
print(result)
