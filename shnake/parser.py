import io
from .lexer import lex as shnake_lex


class LineBuffer:
    """Command line generator designed for shemu's Parser() class

    It takes a file object or None as main argument (`file`).

    If None, a bash like prompt based on the PS1/PS2 strings is
    used as readline() input collector.

    """
    def __init__(self, file):
        if isinstance(file, str):
            file = io.StringIO(file)
        self.file = file


    def readline(self):
        line = self.file.readline()
        if not line:
            return ""
        return line.splitlines()[0] + "\n"



class Parser:

    def __init__(self):
        pass


    def __call__(self, string, lexer=shnake_lex):
        """Interpret `file` data as a command line sequence.

        """
        result = []
        buffer = LineBuffer(string)

        data = ""
        while True:
            if not data:
                data = buffer.readline()
                if not data:
                    return result

            try:
                pipeline = lexer(data[:-1])
                result += pipeline
                data = ""
                if string is None:
                    break

            except SyntaxWarning as error:
                addline = buffer.readline()
                if not addline:
                    raise error
                data += addline

        return result


parse = Parser()
