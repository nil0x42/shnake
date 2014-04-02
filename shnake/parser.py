"""Bash-Like lexical interpreter.

Based on the awsome pyparsing library, it intends to provide
a shell command interpreter, with basic operators support.

"""
import sys, os, io

from pyparsing import (ParserElement, StringEnd, LineEnd, Literal,
                       pythonStyleComment, ZeroOrMore, Suppress,
                       Optional, Combine, OneOrMore, Regex, oneOf,
                       QuotedString, Group, ParseException)


class StringLexer:
    """Bash-like string lexer based on pyparsing.

    It implements a very basic bash inspired lexer that supports
    multicommands, logical operators, pipes, and standard file
    descriptor redirection.

    Its __init__() method takes a string as argument. If the syntax
    if correct, a list() if then returned.
    A list() is a pipeline, aka an instruction block.

    Case study:
    -----------
    >>> StringLex("ls -la /tmp 2>&1 && echo foo'bar'\ ")
    [["ls", "-la", "/tmp", (2, ">", 1)], "&&", ["echo", "foobar "]]

    The example above shows a basic case of string lexing.
    Here, the pipeline (aka the main list()) returned: list, str, list;
    each sub list is a single command, and they are separated by the
    "&&" logical operator. It makes easy post processing for binary
    conditions.
    Also, note that the first command's redirection instruction had
    been parsed as a tuple(), facilitating post processing adaptation.

    """

    def __init__(self):

        ParserElement.setDefaultWhitespaceChars("\t ")

        EOF = StringEnd()
        EOL = ~EOF + LineEnd() # EOL must not match on EOF

        escape = Literal("\\")
        comment = pythonStyleComment
        junk = ZeroOrMore(comment | EOL).suppress()

        ## word (i.e: single argument string)
        word = Suppress(escape + EOL + Optional(comment)) \
        | Combine(OneOrMore( escape.suppress() + Regex(".") |
                             QuotedString("'", escChar='\\', multiline=True) |
                             QuotedString('"', escChar='\\', multiline=True) |
                             Regex("[^ \t\r\n\f\v\\\\$&<>();\|\'\"`]+") |
                             Suppress(escape + EOL) ))

        ## redirector (aka bash file redirectors, such as "2>&1" sequences)
        fd_src = Regex("[0-2]").setParseAction(lambda t: int(t[0]))
        fd_dst = Suppress("&") + fd_src
        # "[n]<word" || "[n]<&word" || "[n]<&digit-"
        fd_redir = (Optional(fd_src, 0) + Literal("<")
                    |Optional(fd_src, 1) + Literal(">"))\
                   +(word | (fd_dst + Optional("-")))
        # "&>word" || ">&word"
        full_redir = (oneOf("&> >&") + word)\
                     .setParseAction(lambda t:("&" ,">", t[-1]))
        # "<<<word" || "<<[-]word"
        here_doc = Regex("<<(<|-?)") + word
        # "[n]>>word"
        add_to_file = Optional(fd_src | Literal("&"), 1) + \
                      Literal(">>") + word
        # "[n]<>word"
        fd_bind = Optional(fd_src, 0) + Literal("<>") + word

        redirector = (fd_redir | full_redir | here_doc
                      | add_to_file | fd_bind)\
                     .setParseAction(lambda token: tuple(token))

        ## single command (args/redir list)
        command = Group(OneOrMore(redirector | word))

        ## logical operators (section splits)
        semicolon = Suppress(";") + junk
        connector = (oneOf("&& || |") + junk) | semicolon

        ## pipeline, aka logical block of interconnected commands
        pipeline = junk + Group(command +
                                ZeroOrMore(connector + command) +
                                Optional(semicolon))

        # define object attributes
        self.LEXER = pipeline.ignore(comment) + EOF
        self.parseException = ParseException


    def __call__(self, string):
        try:
            result = self.LEXER.parseString(string)

        except self.parseException as error:
            index = error.loc

            try:
                char = string[index]
            except:
                if string.strip() == "\\":
                    err = "unexpected EOF after escaped newline '\\\\n'"
                    raise SyntaxWarning(err)
                return []

            if char in "\"\'":
                err = "unexpected EOF while looking for matching %r"
                raise SyntaxWarning(err %char)

            elif (index + 1) == len(string) and char == "\\":
                err = "unexpected EOF after escaped newline '\\\\n'"
                raise SyntaxWarning(err)

            elif string[index:index+2] in ["&&", "||"]:
                raise SyntaxWarning("unexpected end of file")

            else:
                err = "unexpected token %r "
                err += str(error)[str(error).find("("):]
                raise SyntaxError(err %char)

            raise error

        return result[0]




class LineBuffer:
    """Command line generator designed for shemu's Parser() class

    It takes a file object or None as main argument (`file`).

    If None, a bash like prompt based on the PS1/PS2 strings is
    used as readline() input collector.

    """
    def __init__(self, file=None, PS1="$ ", PS2="> "):
        self.PS1 = PS1
        self.PS2 = PS2

        if isinstance(file, str):
            file = io.StringIO(file)
        self.file = file


    def readline(self):
        if self.file is None:
            if not hasattr(self, "_started"):
                self._started = True
                prompt = self.PS1
            else:
                prompt = self.PS2
            return input(prompt) + "\n"

        line = self.file.readline()
        if not line:
            return ""
        print( repr(line.splitlines()[0] + "\n") )
        return line.splitlines()[0] + "\n"



class Parser:

    def __init__(self, stdin=sys.stdin, stdout=sys.stdout,
                 stderr=sys.stderr, PS1="$ ", PS2="> ", cmdfunc=None):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

        self.PS1 = PS1
        self.PS2 = PS2

        self.cmdfunc = cmdfunc


    def __call__(self, file=None):
        """Interpret `file` data as a command line sequence.

        """
        if not isinstance(file, LineBuffer):
            buffer = LineBuffer(file, self.PS1, self.PS2)

        data = ""
        while True:
            if not data:
                data = buffer.readline()
                if not data:
                    return True

            try:
                pipeline = self.parse(data[:-1])
                return_value = self.execute(pipeline)
                data = ""
                if file is None:
                    break

            except SyntaxWarning as error:
                addline = buffer.readline()
                if not addline:
                    raise error
                data += addline

        return return_value


    def parse(self, string):
        try:
            result = LEXER.parseString(string)

        except ParseException as error:
            index = error.loc
            #print(index)
            #print(repr(string))

            try:
                char = string[index]
            except:
                if string.strip() == "\\":
                    err = "unexpected EOF after escaped newline '\\\\n'"
                    raise SyntaxWarning(err)
                return []

            if char in "\"\'":
                err = "unexpected EOF while looking for matching %r"
                raise SyntaxWarning(err %char)

            elif (index + 1) == len(string) and char == "\\":
                err = "unexpected EOF after escaped newline '\\\\n'"
                raise SyntaxWarning(err)

            elif string[index:index+2] in ["&&", "||"]:
                raise SyntaxWarning("unexpected end of file")

            else:
                err = "unexpected token %r "
                err += str(error)[str(error).find("("):]
                raise SyntaxError(err %char)

            raise error

        return result[0]


    def execute(self, pipeline):
        print(pipeline)
        return True


LEXER = StringLexer().LEXER
