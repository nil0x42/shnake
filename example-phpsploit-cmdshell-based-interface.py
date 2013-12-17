"""PhpSploit shell interface.
Unheriting the cmdshell's Cmd class, the PhpSplpoit shell interface

provides interactive use of commands.

"""
import sys, os, difflib, traceback

import core, cmdshell, ui.input
from core import session, plugins

from datatypes import Path, PhpCode
from ui.color import colorize, decolorize


class Cmd(cmdshell.Cmd):

    prompt = colorize('%Lined', 'phpsploit', '%Reset', ' > ')

    nocmd  = "[-] Unknown Command: %s"
    nohelp = "[-] No help for: %s"
    error  = "[!] %s"

    def __init__(self):
        # explicitly run parent's __init__()
        super().__init__()


    def precmd(self, argv):
        """Handle pre command hooks such as session aliases"""
        # Alias Handler
        try: cmds = self.parseline( session.Alias[argv[0]] )
        except (KeyError, IndexError): return argv
        self.interpret(cmds[:-1], precmd=(lambda x: x))
        return cmds[-1] + argv[1:]


    def onexception(self, exception):
        """Add traceback handler to onexception"""
        self.last_exception = exception
        return super().onexception(exception)



    #####################
    ### COMMAND: exit ###
    def do_exit(self, argv):
        """Leave the current shell interface

        SYNOPSIS:
            exit

        DESCRIPTION:
            - Executed from the main shell interface, this command
            leaves the PhpSploit framework.
            - Calling it from a remote shell session simply leaves it,
            backing to the main shell interface
        """
        exit()



    ######################
    ### COMMAND: debug ###
    def complete_debug(self, text, *ignored):
        return ["traceback"]
        keys = ["traceback"]
        return [x+' ' for x in keys if x.startswith(text)]

    def do_debug(self, argv):
        """Core debugging tools

        SYNOPSIS:
            debug
            debug traceback

        DESCRIPTION:
            A command designed to show additionnal informations,
            for core developpement and debugging purposes.

            > debug traceback
            Display last python exception's full stack trace to stdout.
        """
        argv.append('')

        if argv[1] == "traceback":
            e = self.last_exception
            e = traceback.format_exception(type(e), e, e.__traceback__)
            return print( colorize("%Red", "".join(e)) )

        return self.interpret("help debug")



    ########################
    ### COMMAND: exploit ###
    def do_exploit(self, argv):
        """Drop a shell from target server

        SYNOPSIS:
            exploit

        DESCRIPTION:
            Send an HTTP request to the remote server's url, defined
            by the TARGET setting. This first request will try to
            execute the phpsploit's base payload, which retrieves some
            fundamental informations concerning the remote server, such
            as the server signature, and php environment. Il also
            uses the caught informations to determine some environment
            variables, such as CWD or WEB_ROOT.

            NOTE: The TARGET setting must be a remote http(s) url which
            has been infected by the phpsploit backdoor payload.
            Take a look at the documentation (rtfm command), and also
            the "infect" command.
        """
        print("[*] Current backdoor is:")
        print( session.Conf.BACKDOOR() + "\n" )

        if self.__class__.__name__ == "RemoteShell":
            m = ("[*] Use `set TARGET <VALUE>` to use another url as target."
                 "\n[*] To exploit a new server, disconnect from «%s» first.")
            return print( m.format(session.Env.HOST) )

        if session.Conf.TARGET() is None:
            m = ("To run a remote tunnel, the backdoor shown above must be\n"
                 "manually injected in a remote server executable web page.\n"
                 "Then, use `set TARGET <BACKDOORED_URL>` and run `exploit`.")
            return print( colorize("%BoldCyan", m) )

        print("[*] Sending payload to «{}» ...".format(session.Conf.TARGET))
        socket = tunnel.Init() # it raises exception if fails
        remoteShell = ui.shell.Remote()      # start remote shell instance
        remoteShell.cmdqueue = self.cmdqueue # send current command queue
        remoteShell.cmdloop()                # start remote shell interface
        self.cmdqueue = remoteShell.cmdqueue # get back command queue



    ######################
    ### COMMAND: clear ###
    def do_clear(self, argv):
        """Clear the terminal screen

        SYNOPSIS:
            clear

        DESCRIPTION:
            Clear the current visible terminal data, leaving blank the
            screen. Used for visibility purposes.
        """
        return os.system('cls' if os.name=='nt' else 'clear')



    #####################
    ### COMMAND: rtfm ###
    def do_rtfm(self, argv):
        """Read the fine manual

        SYNOPSIS:
            rtfm

        DESCRIPTION:
            Display the PhpSploit's user manual using the "man" command,
            or simply write to standard output it's ascii version on
            OSes which do not provide manpage system.
        """
        txtMan = lambda: print(Path(core.basedir, 'man/phpsploit.txt').read())
        if os.name == 'nt':
            txtMan()
        else:
            cmd = 'man ' + Path(core.basedir, 'man/phpsploit.1')
            return_value = os.system(cmd)
            if return_value is not 0:
                txtMan()



    ########################
    ### COMMAND: session ###
    def complete_session(self, text, *ignored):
        keys = ['save', 'diff']
        # load argument is not available from remote shell:
        if self.__class__.__name__ == "MainShell":
            keys.append('load')
        return [x+' ' for x in keys if x.startswith(text)]

    def do_session(self, argv):
        """PhpSploit session handler

        SYNOPSIS:
            session [load|save|diff] [<FILE>]

        DESCRIPTION:
            The `session` core command handles session instances.
            Sessions can be considered as PhpSploit instances. They
            handle current configuration settings, environment vars,
            command aliases, and remote tunnel attributes (if any).

        USAGE:
            * session [<FILE>]
                Show a nice colored representation of FILE session
                content. If unset, FILE is implicly set to current
                instance's session.
            * session diff [<FILE>]
                Shows a textual representation of the differences
                between FILE and current session state. If FILE is
                not set, $SAVEFILE setting is used. If $SAVEFILE is
                not set, the session's state when framework started
                is used as comparator.
            * session save [<FILE>]
                Dumps the current session instance into the given file.
                If FILE is unset, then the session is saved to $SAVEFILE
                setting, if $SAVEFILE does not exist, then the file path
                "$SAVEPATH/phpsploit.session" is implicitly used.
            * session load [<FILE>]
                Try to load <FILE> as the current session. If unset,
                FILE is implicitly set to "./phpsploit.session".

        EXAMPLES:
            > session load /tmp/phpsploit.session
              - Load /tmp/phpsploit.session.
            > session save
              - Save current state to session's source file (SAVEFILE).

        WARNING:
            The command's `load` argument cannot be used from a remote
            shell interface. It means that a remote shell must be left
            first, in order to load a file stored session file.

        """
        # prevent argv IndexError
        argv += [None, None]

        # session save [<FILE>]
        if argv[1] == 'save':
            session.dump(argv[2])
        # session load [<FILE>]
        elif argv[1] == 'load':
            session.update(argv[2])
        # session diff [<FILE>]
        elif argv[1] == 'diff':
            session.diff(argv[2])
        # sesion [<FILE>]
        else:
            print( session(argv[1]) )



        #    new = decolorize( session ).splitlines()
        #    if argv[2] is None:
        #        old = session.PREVIOUS

        ## session diff
        #if argv[1] == 'diff':
        #    new = decolorize(session.dump()).splitlines()
        #    if argv[2] is None:
        #        old = session.Backup().dump()
        #    else:
        #        old = session.New(argv[2])
        #    old = decolorize(old).splitlines()

        #    color = {' ':'%Reset', '+':'%Red', '-':'%Green', '?':'%Pink'}
        #    for line in difflib.Differ().compare(old, new):
        #        print( colorize(color[line[0]], line) )
        #    return

        ## session <FILE>
        #if argv[1] is not None:
        #    return print( session(argv[1]) )

        ## session
        #return print( session.dump() )




    #####################
    ### COMMAND: lpwd ###
    def do_lpwd(self, argv):
        """Print local working directory

        SYNOPSIS:
            lpwd

        DESCRIPTION:
            This command print the local working directory from your own
            local system, exactly like does the "pwd" shell command on
            unix systems.
        """
        print( os.getcwd() )



    ####################
    ### COMMAND: lcd ###
    def do_lcd(self, argv):
        """Change local working directory

        SYNOPSIS:
            lcd <LOCAL DIRECTORY>

        DESCRIPTION:
            The "lcd" command is an equivalent of the "cd" unix
            command. It must be used to change the current working
            directory of your local system.

            NOTE: This command should not be confused with the
            PhpSploit's "cd" command, which is a plugins doing the same
            on the remotely exploited system.

        EXAMPLES:
            > lcd ~
            > lcd /tmp
        """
        # only one argument must be supplied
        if len(argv) != 2:
            return self.interpret('help lcd')

        os.chdir( os.path.expanduser(argv[1]) )



    ####################
    ### COMMAND: source ##
    def do_source(self, argv):
        """Execute a PhpSploit script file

        SYNOPSIS:
            source <LOCAL FILE>

        DESCRIPTION:
            This command takes a file name as argument, and executes
            its content lines as a list of PhpSploit commands.

        EXAMPLES:
            > source /tmp/spl01t-script.phpsploit
              - Run the given script file's content, line by line
        """
        if len(argv) != 2:
            return self.interpret("help source")

        self.interpret( open(argv[1], 'r').read() )



    ####################
    ### COMMAND: set ###
    def complete_set(self, text, *_):
        """Use settings as `set` completers (case insensitive)"""
        result = []
        for key in session.Conf.keys():
            if key.startswith( text.upper() ):
                result.append(key)
        return result

    def do_set(self, argv):
        """View and edit settings

        SYNOPSIS:
            set [<NAME> [+] ["<VALUE>"]]

        DESCRIPTION:
            PhpSploit configuration settings manager.
            The settings are a collection of core variables that affect
            the framework's core behavior. Any setting take a default
            value, that can be manually modified.

            > set
            - Display all current settings

            > set <STRING>
            - Display all settings whose name starts with STRING.

            > set <NAME> "value"
            - Change the NAME setting to "value". If the value is not valid,
            no changes are made.

            > set <NAME> "file:///path/to/file"
            - Set NAME setting's value into a RandLine buffer whose value
            binds to the external file "/path/to/file". It means that the
            setting's effective value is dynamic, and on each call to it,
            the file's content will be loaded if available, and the
            value is a random line from the file/buffer.

            > set <NAME> +
            - Open the setting value for edition as a multiline buffer
            with TEXTEDITOR. The buffer can then be edited, and once saved,
            the setting will take the buffer's value, except if there are
            no valid lines.

            > set <NAME> + "value"
            - Add "value" as a setting possible choice. If converts the
            current setting into a RandLine buffer if it was not.

            > set <NAME> + "file:///path/to/file"
            - Rebind NAME setting to the given file path, even if it does
            not exist at the moiment it had been set. It means that each
            time the setting's value is called, a try is made to load the
            file's content as new buffer if it exists/is valid, and
            keeps the old one otherwise.


        BEHAVIOR
            - Settings are pre declared at start. It means that new ones
            cannot be declared.

            - The convention above does not apply for settings whose name
            start with "HTTP_", because this kind of variable are
            automatically used as custom headers on http requests. For
            example, `set HTTP_ACCEPT_LANGUAGE "en-CA"` will set the
            "Accept-Language" http header to the specified value.

            NOTE: The 'set' operating scope is limited to the current
            PhpSploit session. It means that persistant settings value
            changes must be defined by the hand in the user
            configuration file.
        """
        # `set [<PATTERN>]` display concerned settings list
        if len(argv) < 3:
            print(session.Conf( (argv+[""])[1] ))

        # buffer edit mode
        elif argv[2] == "+":
            # `set <VAR> +`: use TEXTEDITOR as buffer viewer in file mode
            if len(argv) == 3:
                # get a buffer obj from setting's raw buffer value
                buffer = Path(); buffer.write( session.Conf[argv[1]].buffer )
                # try to edit it through TEXTEDITOR, and update it
                # if it has been modified.
                if buffer.edit():
                    session.Conf[argv[1]] = buffer.read()
            # `set <VAR> + "value"`: add value on setting possible choices
            else:
                session.Conf[argv[1]] += " ".join(argv[3:])
        # `set <VAR> "value"`: just change VAR's "value"
        else:
            session.Conf[argv[1]] = argv[2]



    ####################
    ### COMMAND: env ###
    def complete_env(self, text, *ignored):
        """Use env vars as `env` completers (case insensitive)"""
        result = []
        for key in session.Conf.keys():
            if key.startswith( text.upper() ):
                result.append(key)
        return result

    def do_env(self, argv):
        """Environment variables handler

        SYNOPSIS:
            env [<NAME> ["<VALUE>"|None]]

        DESCRIPTION:
            The PhpSploit environment variables are created once a remote
            server tunnel is opened through the interface.
            These variables are used by the core and some plugins to
            correctly manage and know server's current state.

            > env
            - Display all current env vars

            > env <STRING>
            - Display all env vars whose name starts with STRING.

            > env <NAME> "<VALUE>"
            - Set NAME env variable's value to VALUE.

            > env <NAME> None
            - Remove NAME environment variable.

        CASE STUDY:
            The `CWD` environment variable changes each time the `cd`
            command is used. It contains the current directory path of
            the session. When a remote server exploitation session starts,
            it is defaultly set to the server's HOME directory if,
            available, otherwise, it is set to the root web directory.
            This environment variable may be manually changed by using the
            `env CWD "/other/path"`, but it is generally not recommended
            since it can broke some plugins if the value is not a remote
            accessible absolute path.

        BEHAVIOR:
            - At framework start, the env vars array is empty.

            - Env vars array is filled once a remote server shell is
            started through the PhpSploit framework.

            - Some envionment variables, such as CWD and WEB_ROOT are
            crucial for remote session consistency. Be careful before
            manually editing them.

            - Plugins that need persistent server based variables may and
            must use env vars. For example, the `mysql` plugin creates a
            `MYSQL_CRED` environment variable that contains remote
            database connection credentials when using `mysql commect`,
            it allows the plugin to not require setting user/pass/serv
            informations on each remote sql command.

            - Unlike settings, env vars do not provide dynamic random
            values. Setting a value is simply interpreted as a string,
            apart for the special "None" value, that deletes the variable.
        """
        # `env [<PATTERN>]` display concerned settings list
        if len(argv) < 3:
            return print(session.Env( (argv+[""])[1] ))

        # `env <NAME> <VALUE>`
        session.Env[argv[1]] = " ".join(argv[2:])



    ########################
    ### COMMAND: backlog ###
    def do_backlog(self, argv):
        """Open last command's output with text editor

        SYNOPSIS:
            backlog

        DESCRIPTION:
            Get the last command's output data opened through
            $TEXTEDITOR setting on a temporary file.

            NOTE: Last command buffer is colorless. It means that
            it does not contains ansy ANSI terminal color codes.
        """
        backlog = Path()
        backlog.write(sys.stdout.backlog)
        backlog.edit()
        return



    #####################
    ### COMMAND: help ###
    def do_help(self, argv):
        """Show commands help

        SYNOPSIS:
            help [<COMMAND>]

        DESCRIPTION:
            It displays help message for any command, including
            plugins.
            - Without arguments, the whole available commands, sorted
              by category, are displayed including a summary line for
              each one.
            - To display the full help message of a specific command,
              it must be given as argument.

            NOTE: A plugin command may also be called with "--help"
            a argument, resulting to the same as "help <plugin>".

        EXAMPLES:
            > help
              - Displpay the full help, sorted by category
            > help clear
              - Display the help for the "clear" command
        """
        # If more than 1 argument, help to help !
        if len(argv) > 2:
            return self.interpret('help help')

        # collect the command list from current shell
        sys_commands = self.get_commands(self)

        def get_doc(cmdName):
            """return the docstring lines list of specific command"""
            # try to get the doc from the plugin method
            try:
                docString = self.plugins.get(cmdName, 'help')
            except:
                docString = None
            # or try to get it from the shell commands
            if cmdName in sys_commands:
                docString = getattr(self, 'do_'+cmdName).__doc__
            # else try to get it from the core commands
            if docString is None:
                try:
                    docString = getattr(CoreShell, 'do_'+cmdName).__doc__
                except:
                    docString = None
            # a list, even empty must be returned in any case
            if docString is None:
                return( list() )
            return( docString.strip().splitlines() )

        def get_description(docLines):
            """return the command description (1st docstring line)"""
            try:
                return( docLines[0].strip() )
            except:
                return( color(33) + 'No description' + color(0) )

        def doc_help(docLines):
            """print the formated command's docstring"""
            # reject empty docstrings (description + empty line)
            if len(docLines) < 2:
                return(None)
            docLines.pop(0) # remove the description line
            while not docLines[0].strip():
                docLines.pop(0) # remove heading empty lines

            # remove junk leading spaces (due to python indentation)
            trash = len( docLines[0] ) - len( docLines[0].lstrip() )
            docLines = [ line[trash:].rstrip() for line in docLines ]

            # hilight lines with no leading spaces (man style)
            result = str()
            for line in docLines:
                if line == line.lstrip():
                    line = color(1) + line + color(0)
                result += line + P_NL

            print(result)

        # get full help on a single command
        if len(argv) == 2:
            doc = get_doc(argv[1])
            # if the given argument if not a command, return nohelp err
            if not doc:
                print( self.nohelp %raw_repr(argv[1]) )
                return(None)

            # print the heading help line, which contain description
            print( P_NL + P_inf + argv[1] + ": " +
                   get_description(doc) + P_NL )

            # call the help_<command> method, otherwise, print it's docstring
            try:
                getattr( self, 'help_'+argv[1] )()
            except:
                doc_help(doc)
            return(None)

        # display the whole list of commands, with their description line

        # set maxLength to the longest command name, and at least 13
        maxLength = max( 13, len(max(sys_commands, key=len)) )

        # split sys_commands into shell and core command categories
        core_commands  = self.get_commands(CoreShell)
        shell_commands = [x for x in sys_commands if x not in core_commands]
        help = [('Core Commands', core_commands),
                ('Shell Commands', shell_commands)]

        # adds plugin category if we are in the remote shell
        if self.shell_name == 'remote':
            for category in self.plugins.categories():
                name = category.replace('_', ' ').capitalize()
                items = self.plugins.list_category(category)

                # rescale maxLength in case of longer plugin names
                maxLength = max( maxLength, len(max(items, key=len)) )
                help += [ (name+' Plugins', items) ]

        # print commands help, sorted by groups
        cmdColumn = ' ' * (maxLength-5)
        for groupName, groupCommands in help:

            # display group (category) header block
            underLine = '=' * len(groupName)
            print( P_NL + groupName +  P_NL + underLine      + P_NL +
                   '    Command' + cmdColumn + 'Description' + P_NL +
                   '    -------' + cmdColumn + '-----------' + P_NL )

            # display formated command/description pairs
            groupCommands.sort()
            for cmdName in groupCommands:
                spaceFill = ' ' * ( maxLength - len(cmdName) +2 )
                description = get_description( get_doc(cmdName) )
                print( '    ' + cmdName + spaceFill + description )
            print('')


    def except_OSError(self, exception):
        """Fix OSError args, removing errno, and adding filename"""
        if isinstance(exception.errno, int):
            exception.args = (exception.strerror,)
        if exception.filename is not None:
            exception.args += ("«{}»".format(exception.filename),)
        return exception
