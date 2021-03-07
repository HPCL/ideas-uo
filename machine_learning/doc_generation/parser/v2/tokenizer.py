from lexer import lex

import string
import sys
import uuid

pairs = []

for char in string.ascii_lowercase:
    name = f'LOWERCASE_{char.upper()}'
    regex = r'{}'.format(char)
    pairs.append((name, regex))

for char in string.ascii_uppercase:
    name = f'UPPERCASE_{char.upper()}'
    regex = r'{}'.format(char)
    pairs.append((name, regex))

for char in string.digits:
    name = f'DIGIT_{char}'
    regex = r'{}'.format(char)
    pairs.append((name, regex))

punctuation = {
    r'!': 'EXCLAMATION_MARK',
    r'"': 'DOUBLE_QUOTE',
    r'\#': 'HASHTAG',
    r'\$': 'DOLLAR_SIGN',
    r'%': 'PERCENT_SIGN',
    r'&': 'AMPERSAND',
    r'\'': 'SINGLE_QUOTE',
    r'\(': 'OPEN_PAREN',
    r'\)': 'CLOSE_PAREN',
    r'\*': 'ASTERISK',
    r'\+': 'PLUS_SIGN',
    r',': 'COMMA',
    r'-': 'HYPHEN',
    r'\.': 'PERIOD',
    r'/': 'FORWARD_SLASH',
    r':': 'COLON',
    r';': 'SEMICOLON',
    r'<': 'OPEN_ANGLE',
    r'>': 'CLOSE_ANGLE',
    r'=': 'EQUAL_SIGN',
    r'\?': 'QUESTION_MARK',
    r'@': 'AT_SIGN',
    r'\[': 'OPEN_BRACKET',
    r'\\': 'BACK_SLASH',
    r'\]': 'CLOSE_BRACKET',
    r'\^': 'CARET',
    r'_': 'UNDERSCORE',
    r'`': 'BACKTICK',
    r'{': 'OPEN_CURLYBRACE',
    r'\|': 'PIPE',
    r'\}': 'CLOSE_CURLYBRACE',
    r'~': 'TILDE',
    r'\s{1}': 'SPACE'
}

for char in punctuation.keys():
    name = punctuation[char]
    regex = r'{}'.format(char)
    pairs.append((name, regex))

start = uuid.uuid1().hex
end = uuid.uuid1().hex
pairs.append(('SOL', r'{}'.format(start)))
pairs.append(('EOL', r'{}'.format(end)))

tokens = []

module = sys.modules[__name__]

for token, regex in pairs:
    variable = f't_{token}'
    tokens.append(token)
    setattr(module, variable, regex)


def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

lexer = lex(start=start, end=end)

if __name__ == '__main__':
    data = '{(\w+)}'
    data = '^author (.*)'
    data = '.*\.(a|so|dylib)$'
    #data = 'Content-Type:[^\r\n]+'
    data = '\.'

    lexer.input(data)

    while True:
        token = lexer.token()
        if not token: break
        print(token)
