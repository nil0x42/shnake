from . import shell
try:
    from .parser import Parser
except ImportError:
    Parser = None;

class Cmd(shell.Cmd):

    def __init__(self, completekey='tab', stdin=None, stdout=None):
        super().__init__(completekey=completekey, stdin=stdin, stdout=stdout)

    def parseline(self, string, interactive=True):
        return super().parseline(string=string, interactive=interactive)
        # if Parser is None:
        #     super().parseline(string=string, interactive=interactive)
        # else
        #     parser = Parser()
