"""

Standard cmd lib usage:
>>> import cmd

>>> class HelloWorld(cmd.Cmd):
>>> """Simple command processor example."""

>>> def do_greet(self, line):
>>> print "hello"

>>> def do_EOF(self, line):
>>> return True

>>> if __name__ == '__main__':
>>> HelloWorld().cmdloop()

Shemu usage:
>>> import shemu
>>> "???"

"""
import sys, io

class Cmd:
    """Command object with shell like standard attributes

    Usage:
    >>> import sys, shemu
    >>> cmd = shemu.Cmd(["ls", "-la", "/"])
    >>> cmd.stdin = open("/etc/stdin", "r")
    >>> cmd.stdout = sys.stdout
    >>> return int(cmd.exec())

    """
    _fdnames = ["stdin", "stdout", "stderr"]

    fd = {}
    env = {}

    def __init__(self, parent=None, cmdobj=None, **kwargs):
        """Instantiates a new command object.

        It takes an iterable representation of the triggering command.
        Optionally, object attributes (such as stdin, stdout and stderr)
        can be set on instanciation by defining them as named arguments.

        Usage:
        >>> inputFile = open("/tmp/in")
        >>> outputFile = open("/tmp/out", "w")
        >>> cmd = Cmd(["command", "argument"], stdin=inputFile)
        >>> cmd.stdout = outputFile
        >>> if cmd.exec():
        >>>     print("success")

        """
        # set std* default values on kwargs
        for fd in self._fdnames:
            kwargs.setdefault(fd, None)

        # define kwargs as self attributes
        for name, value in kwargs.iteritems():
            # self.std* = sys.std* if std* is None
            if name in self._fdnames and value is None:
                value = getattr(sys, name)
            setattr(self, name, value)

        if cmdobj is None:
            cmdobj = self.stdin
        elif isinstance(cmdobj, str):
            cmdobj = io.StringIO(cmdobj)

        # check if cmdobj is a file
        try:
            # is is a tty, use dedicated LineBuffer object (file emulator)
            if cmdobj.isatty():
                # XXX: HANDLE 
        # otherwise ensure it is an iterable
        except AttributeError:
            try:
                iter(cmdobj)
            except TypeError:
                raise ValueError("cmdobj: must be a string, file or iterable")

        try:
            assert callable( type(cmdobj.read) )
        except AssertionError, AttributeError:
            if 

        # if cmdobj is a file object
        if hasattr(cmdobj, "isatty") and callable(cmdobj.isatty):
            if cmdobj.isatty():
                #XXX: set up a LineBuffer
            else:
                #XXX: do nothing, keep file as it is




        if not isinstance(file, LineBuffer):
            buffer = LineBuffer(file, self.PS1, self.PS2)


    def exec(self)
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

        return CmdReturnVal(return_value)


    def __call__(self):
        """An alternative to the exec() method"""
        return self.exec()


    def __getattr__(self, name):
        """Make standard file descriptors reachable by their names"""
        try: return self.fd[ self._fdnames.index(name) ]
        except ValueError: return super().__getattr__(name)


    def __setattr__(self, name, value):
        """Make standard file descriptors settable by their names"""
        try: self.fd[ self._fdnames.index(name) ] = value
        except ValueError: super().__setattr__(name, value)


    def __dir__(self):
        """Add self._descriptor items (std*) to attributes list"""
        return super().__dir__() + self._fdnames




class CmdReturnVal(int):
    """Bash-Like return value.

    CmdReturnVal extends python standard integers, and emulates
    shell int boolean behavior.

    Example:
    >>> bool( CmdReturnVal(0) )
    True
    >>> bool( CmdReturnVal(-1) )
    False
    >>> bool( CmdReturnVal(1) )
    False

    """
    def __new__(cls, value):
        return int.__new__(cls, int(value))

    def __bool__(self):
        if int(self) == 0:
            return True
        return False




class StringLexer:
    """Bash-like string lexer based on pyparsing.

    Implement a basic bashlike parser/lexer which handles
    multi command, logical operators separations, pipes
    and std* file descriptor redirections.

    Class instanciation builds the pyparsing based lexer.
    Instance can then used as a function (from __call__() method)
    in order to lex some strings.

    Usage:
    >>> lexer = StringLex() # build lexer
    >>> lexer("ls -la /tmp 2>&1 && echo foo'bar'\ ") # use it as a function
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
        from pyparsing import (ParserElement, StringEnd, LineEnd, Literal,
                               pythonStyleComment, ZeroOrMore, Suppress,
                               Optional, Combine, OneOrMore, Regex, oneOf,
                               QuotedString, Group, ParseException)

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
                     .setParseAction(lambda t:("&",">",t[-1]))
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

        except self.ParseException as error:
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

            elif index+1 == len(string) and char == "\\":
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
