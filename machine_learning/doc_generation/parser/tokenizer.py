import ply.lex as lex

import string

tokens = (
    'OPEN_PARENS',
    'CLOSE_PARENS',
    'OPEN_NONCAPTURE_PARENS',
    'OPEN_POSITIVE_LOOKAHEAD_PARENS',
    'OPEN_NEGATIVE_LOOKAHEAD_PARENS',
    'ANCHOR',
    'WORD',
    'NUMBER',
    'WHITESPACE_SEPARATOR',
    'NEWLINE',
    'STRING',
    'OPEN_BRACKETS',
    'CLOSE_BRACKETS',
    'OPEN_CURLYBRACES',
    'CLOSE_CURLYBRACES',
    'OPEN_ANGLE',
    'CLOSE_ANGLE',
    'SINGLE_QUOTE',
    'DOUBLE_QUOTE',
    'TILDE',
    'BACK_QUOTE',
    'EXCLAMATION_MARK',
    'AT_SIGN',
    'POUND_SIGN',
    'DOLLAR_SIGN',
    'PERCENT_SIGN',
    'CARET_SIGN',
    'AMPERSAND',
    'ASTERISK',
    'MINUS_SIGN',
    'UNDERSCORE',
    'PLUS_SIGN',
    'EQUALS',
    'PIPE',
    'BACK_SLASH',
    'FORWARD_SLASH',
    'COLON',
    'SEMICOLON',
    'COMMA',
    'PERIOD',
    'QUESTION_MARK',
    'SPACE',
    'TAB'
)

t_OPEN_PARENS = r'\('
t_CLOSE_PARENS = r'\)'
t_OPEN_NONCAPTURE_PARENS = r'\(\?:'
t_OPEN_POSITIVE_LOOKAHEAD_PARENS = r'\(\?='
t_OPEN_NEGATIVE_LOOKAHEAD_PARENS = r'\(\?!'
t_ANCHOR = r'\\[bB]'
t_WORD = r'\\w\+|\\w\*'
t_NUMBER = r'\\d\+|\\d\+\.\\d\*|\.\\d\+'
t_WHITESPACE_SEPARATOR = r'\\s\+|\\s\*|\\S'
t_NEWLINE = r'\\n\+|\\n\*'
t_STRING = r'\.\+|\.\*'
t_OPEN_BRACKETS = r'\['
t_CLOSE_BRACKETS = r'\]'
t_OPEN_CURLYBRACES = r'\{'
t_CLOSE_CURLYBRACES = r'\}'
t_OPEN_ANGLE = r'\<'
t_CLOSE_ANGLE = r'\>'
t_SINGLE_QUOTE = r'\''
t_DOUBLE_QUOTE = r'\"'
t_TILDE = r'\~'
t_BACK_QUOTE = r'\`'
t_EXCLAMATION_MARK = r'\!'
t_AT_SIGN = r'\@'
t_POUND_SIGN = r'\#'
t_DOLLAR_SIGN = r'\$'
t_PERCENT_SIGN = r'\%'
t_CARET_SIGN = r'\^'
t_AMPERSAND = r'\&'
t_ASTERISK = r'\*'
t_MINUS_SIGN = r'\-'
t_UNDERSCORE = r'\_'
t_PLUS_SIGN = r'\+'
t_EQUALS = r'\='
t_PIPE = r'\|'
t_BACK_SLASH = r'\\'
t_FORWARD_SLASH = r'\/'
t_COLON = r'\:'
t_SEMICOLON = r'\;'
t_COMMA = r'\,'
t_PERIOD = r'\.'
t_QUESTION_MARK = r'\?'
t_SPACE = r'\ '
t_TAB = r'\t'

literals = list(string.printable)

def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

lexer = lex.lex()

if __name__ == '__main__':
    data = '{(\w+)}'
    data = '^author (.*)'
    lexer.input(data)

    while True:
        token = lexer.token()
        if not token: break
        print(token)
