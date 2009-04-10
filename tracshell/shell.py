import os, sys
import cmd
import subprocess
import tempfile
import xmlrpclib
import shlex
import re

from pydoc import pager
from tracshell.helpers import get_termsize
from tracshell.settings import Settings
from tracshell.trac import Trac

VERSION = 0.1

settings = Settings()

DEFAULT_ALIASES = {
    'q': 'query $0',
    'v': 'view $0',
    'e': 'edit $0',
    'c': 'create $0',
    'log': 'changelog $0',
    'Q': 'quit',
}

RESERVED_COMMANDS = set(['query', 'view', 'edit', 'create', 'changelog',
    'quit'])

TERM_SIZE = get_termsize(sys.stdout)

class Shell(object):
    """
    Shell is a constructor class for building TracShell instances.

    It queries the Trac server for the methods available to the user
    and creates a TracShell instance with only matching methods.

    >> from tracshell.shell import Shell
    >> trac = Shell('me', 'mypass', 'http://trac.myserver.org')
    >> trac.run()
    """

    def __init__(self, username, password, host, port=80,
                 secure=False, rpc_path='/login/xmlrpc'):
        """
        Initialize the Trac interface and build the TracShell instance

        Arguments:
        - `username`: the user to authenticate as
        - `password`: a valid password
        - `host`: the host name serving the Trac instance
        - `port`: defaults to 80
        - `secure`: whether https (SSL) is used
        - `rpc_path`: the path to the XML-RPC interface of the Trac interface
        """
        self._username = username
        self._password = password
        self._host = host
        self._port = port
        self._rpc_path = rpc_path
        self._secure = secure
        self._trac = Trac(self._username,
                          self._password,
                          self._host,
                          self._port,
                          self._secure,
                          self._rpc_path)
        shell = TracShell
        server_methods = self._trac._server.system.listMethods()
        shell_methods = [getattr(shell, method)
                         for method in dir(shell)
                         if method.startswith('do_')]
        shell_methods = filter(lambda x: hasattr(x, 'trac_method'),
                               shell_methods)
        for method in shell_methods:
            if method.trac_method not in server_methods:
                delattr(shell, method.__name__)
        self.shell = shell(self._trac)

    def run(self):
        self.shell.cmdloop()

class TracShell(cmd.Cmd):
    """
    TracShell is a shell interface to a Trac instance.
    
    It uses and XML-RPC interface to Trac provided by:

        http://trac-hacks.org/wiki/XmlRpcPlugin#DownloadandSource
    """

    def __init__(self, trac_interface):
        """ Initialize the XML-RPC interface to a Trac instance.

        Arguments:
        - `trac_interface`: an initialized tracshell.trac.Trac instance
        """
        self._editor = self._find_editor()
        self.trac = trac_interface

        # set up shell options and shortcut keys
        cmd.Cmd.__init__(self)
        self.prompt = "trac->> "
        self.ruler = '-'
        self.intro = "Welcome to TracShell!\nType `help` for a list of commands"
        self.aliases = {}
        for k, v in settings.aliases.items():
            if k not in RESERVED_COMMANDS:
                self.aliases[k] = v
        # built-in shortcuts have priority, so they overwrite aliases
        self.aliases.update(DEFAULT_ALIASES)
    
    def _edit_ticket(self, initial_lines):
        """
        Launches a text editor so that the user can edit `initial_lines`,
        which are in field=val format.
        Returns a dictionary of key: val pairs or None if no edition took 
        place or if something went wrong.
        
        Arguments:
        - `initial_lines`: a list of lines to be edited
        """
        fname = tempfile.mktemp()
        fh = open(fname, "w")
        fh.writelines(initial_lines)
        fh.close()
        mtime_before = os.stat(fname).st_mtime
        try:
            subprocess.call([self._editor, fname])
        except AttributeError:
            print "No editor set, see `help editors`"
            return None
        mtime_after = os.stat(fname).st_mtime
        if not (mtime_after > mtime_before): # no edition took place
            print "Edition aborted"
            return None
        try:
            fh = open(fname, "r")
            content = fh.read()
            fh.close()
            # matches a word followed by a '=' with the rest of the content, which ends when the
            # lookahead reveals either another word+'=' or the end of the string.
            # Note: This can be fooled by starting a line with a space-less word followed by a '='
            field_pattern = r"^(\S*?)=(.*?)(?=^\S*=|\Z)"
            matches = re.findall(field_pattern, content, re.DOTALL | re.MULTILINE)
            data = dict(matches)
            return data
        except ValueError, e:
            print "Something went wrong or the file was formatted"
            print "wrong. Please try submitting the ticket again"
            print "or file a bug report with the TracShell devs."
            print "Error: %s" % unicode(e)
            return None
    
    def _find_editor(self):
        """
        Try to find the users' editor by testing
        the $EDITOR environment variable, warn the
        user if one isn't found and return None.
        """
        try:
            return settings.editor
        except AttributeError:
            try:
                return os.environ['EDITOR']
            except KeyError:
                print "Warning: No editor found, see `help editors`"
                return None
    
    def _parse_query_str(self, q):
        """
        Parse a query string

        Arguments:
        - `string`: A string in the form of field1=val field2="long val"
        """
        data = dict([item.split('=') for item in shlex.split(q)])
        return data
    
    def precmd(self, line):
        parts = line.split(' ')
        cmd = parts[0]
        if cmd in self.aliases:
            cmd = self.aliases[cmd]
            args = parts[1:]
            unused_args = [] # they go into $0 if it exists
            for index, arg in enumerate(args):
                param_placeholder = '$%d' % (index + 1)
                if param_placeholder in cmd:
                    cmd = cmd.replace(param_placeholder, arg)
                else:
                    unused_args.append(arg)
            if unused_args and '$0' in cmd:
                cmd = cmd.replace('$0', ' '.join(unused_args))
            return cmd
        else:
            return line

    def do_query(self, query):
        """
        Query for tickets in Trac

        Shortcut: q

        Arguments:
        - `query`: A Trac query string (see `help queries` for more info)
        """
        if not(query.strip()):
            print "No query specified."
            return

        tickets = self.trac.query_tickets(query)
        output = []
        if tickets:
            for ticket in tickets:
                (id, date, mod, data) = ticket
                output.append("%5s: [%s] %s" % (id,
                                                data['status'].center(8),
                                                data['summary']))
            if hasatter(settings, 'pager'):
                if len(output) > TERM_SIZE[0]:
                    pager('\n'.join(output))
                else:
                    print '\n'.join(output)
            else:
                print '\n'.join(output)
        else:
            print "Query returned no results"
    do_query.trac_method = 'ticket.query'

    def do_view(self, ticket_id):
        """
        View a specific ticket in trac

        Shortcut: v

        Arguments:
        - `ticket_id`: An integer id of the ticket to view
        """
        try:
            ticket = self.trac.get_ticket(int(ticket_id))
        except ValueError:
            print "Invalid ticket nr specified."
            return

        if ticket:
            output = []
            (id, created, modified, data) = ticket
            data['created'] = created
            data['last_modified'] = modified

            output.append("Details for Ticket: %s" % id)
            for k, v in data.iteritems():
                output.append("%15s: %s" % (k, v))
            if hasattr(settings, 'pager'):
                if settings.pager and len(output) > TERM_SIZE[0]:
                    pager('\n'.join(output))
                else:
                    print '\n'.join(output)
            else:
                print '\n'.join(output)
        else:
            print "Ticket %s not found" % ticket_id
    do_view.trac_method = 'ticket.get'

    def do_changelog(self, ticket_id):
        """
        View the changes to a ticket

        Shortcut: log
        
        Arguments:
        - `ticket_id`: An integer id of the ticket to view
        """
        try:
            changes = self.trac.get_ticket_changelog(int(ticket_id))
        except ValueError:
            print "Invalid ticket id specified."
            return

        if changes:
            output = []
            output.append("Changelog for Ticket %s:" % ticket_id)
            for change in changes:
                (time, author, field, old, new, pflag) = change
                output.append("%s by %s:" % (time, author))
                output.append("Changed '%s' from '%s' to '%s'\n" % (field,
                                                                    old,
                                                                    new))
            if hasattr(settings, 'pager'):
                if len(output) > TERM_SIZE[0]:
                    pager('\n'.join(output))
                else:
                    print '\n'.join(output)
            else:
                print '\n'.join(output)
    do_changelog.trac_method = 'ticket.changeLog'

    def do_create(self, param_str):
        """
        Create and submit a new ticket to Trac instance

        trac->> create `summary`

        This feature works but is still under development.
        Please report any bugs you find.

        Shortcut: c

        Arguments:
        - `summary`: Title of the ticket
        """
        # would like to launch a blank template tmp file
        # and parse the returned file
        try:
            template_lines = ["summary=%s\n" % param_str,
                              "reporter=\n",
                              "description=\n",
                              "type=\n",
                              "priority=\n",
                              "component=\n",
                              "milestone=\n",
                              "version=\n",
                              "keywords=\n"]
            data = self._edit_ticket(template_lines)
            if data is None:
                return False
            try:
                id = self.trac.create_ticket(data.pop("summary"),
                                             data.pop("description"),
                                             data)
            except Exception, e:
                print "A problem has occurred communicating with Trac."
                print "Error: %s" % e
                print "Please file a bug report with the TracShell devs."
                return False
            if id:
                print "Created ticket %s: %s" % (id, param_str)
        except Exception, e:
            print e
            print "Try `help create` for more info"
            pass
    do_create.trac_method = 'ticket.create'

    def do_edit(self, param_str):
        """
        Edit a ticket in Trac

        trac->> edit `ticket_id` field1=value1 field2=value2

        This feature is still under development.
        Please report any bugs you find.

        Shortcut: e
        
        Arguments:
        - `ticket_id`: the id of the ticket to edit
        """
        
        try:
            ticket_id, changes = param_str.split(' ', 1)
        except ValueError: # No changes specified
            ticket_id = param_str
            changes = None
        try:
            ticket = self.trac.get_ticket(int(ticket_id))
        except ValueError:
            print "Invalid ticket id specified."
            return
        if not ticket:
            print "Ticket %s not found" % ticket_id
            return
        id, created, modified, orig_data = ticket
        if changes is None: # Summon the editor
            orig_data['comment'] = "Your comment here"
            lines = ['%s=%s\n' % (k, v.rstrip())
                     for k, v in orig_data.iteritems()]
            data = self._edit_ticket(lines)
            if data is None:
                return False
            # submit the difference between what went into the editor
            # and what came out
            for k, v in orig_data.iteritems():
                if v in data[k]:
                    data.pop(k)
        else: # just do the update
            data = self._parse_query_str(changes)
        if 'comment' in data:
            comment = data.pop('comment')
        else:
            comment = ''
        self.trac.update_ticket(id, comment, data)
        print "Updated ticket %s: %s" % (id, comment)
    
    do_edit.trac_method = 'ticket.update'

    # option setter funcs
    # see `do_set`

    def set_editor(self, editor):
        """
        Set the path to the editor to invoke for manipulating
        tickets, comments, etc.

        Arguments:
        - `editor`: the path to an editor
        """
        if os.path.exists(editor.split(' ')[0]):
            self._editor = editor
        else:
            raise ValueError, "Not a valid path to an editor"

    # misc support funcs

    def do_set(self, query_str):
        """
        Set an option using a query string.

        Valid options are:

        - `editor`: A valid path to your favorite editor

        See `help queries` for more information.
        
        Arguments:
        - `query_str`: A query string of options to set
        """
        try:
            data = self._parse_query_str(query_str)
        except ValueError, e:
            print "Warning: Invalid query string for `set`"
            print "Try fixing %s" % query_str
            print "See `help queries` for more information."
            pass

        for k, v in data.iteritems():
            if hasattr(self, 'set_%s' % k):
                try:
                    getattr(self, 'set_%s' % k)(v)
                except Exception, e:
                    print e
                    pass
    
    def do_quit(self, _):
        """
        Quit the program

        Shortcut: Q
        """
        # cmd.Cmd passes an arg no matter what
        # which we don't care about here.
        # possible bug?
        print "Goodbye!"
        sys.exit()

    # misc help functions

    def help_queries(self):
        text = """
        Query strings take the form of:

           field=value

        Multiple queries can be stringed together:

           field1=value1 field2="long value2"

        Values with spaces should be quoted.

        """
        print text

    def help_editors(self):
        text = """
        TracShell uses your preferred text editor for
        editing and creating tickets, comments, and so
        forth. It tries to find your preferred editor
        by looking for it in the $EDITOR environment
        variable.

        If not set, you may get a warning. In this case,
        see the `help set` command for setting up options
        inside the TracShell.
        """
        print text

    def help_aliases(self):
        text = "Here is the list of the currently defined aliases:"
        print text
        for k, v in self.aliases.items():
            print "%15s: %s" % (k, v)
    

