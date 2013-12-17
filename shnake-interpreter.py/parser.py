#!/usr/bin/python

from pyparsing import *

ParserElement.setDefaultWhitespaceChars("\t ")

EOF = StringEnd()
EOL = ~EOF + LineEnd() # EOL must not match on EOF

escape = Literal("\\")
comment = pythonStyleComment
junk = ZeroOrMore(comment | EOL).suppress()

# word (i.e: single argument string)
word = Suppress(escape + EOL + Optional(comment)) \
| Combine(OneOrMore( escape.suppress() + Regex(".") |
                     QuotedString("'", escChar='\\', multiline=True) |
                     QuotedString('"', escChar='\\', multiline=True) |
                     Regex("[^ \t\r\n\f\v\\\\$&<>();\|\'\"`]+") |
                     Suppress(escape + EOL) ))

#command = Group(OneOrMore(redirector | word))
command = Group(OneOrMore(word))

# commands logical connectors
semicolon = Suppress(";") + junk
connector = (oneOf("&& || |") + junk) | semicolon

# pipeline, aka logical block of interconnected commands
pipeline = junk + Group(command +
                        ZeroOrMore(connector + command) +
                        Optional(semicolon))

PARSER = pipeline.ignore(comment) + EOF
