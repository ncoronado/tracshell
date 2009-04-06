import os, sys
import cmd
import subprocess
import tempfile
import xmlrpclib
import shlex

from pydoc import pager
from settings import Settings
from trac import Trac

VERSION = 0.1

settings = Settings()

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
        self.shortcuts = self._build_shortcuts()

    def _build_shortcuts(self):
        """
        Return a dictionary of shortcut -> command-name
        """
        cmd_names = filter(lambda x: x.startswith('do_'), self.get_names())
        cmd_fns = [getattr(self, cmd) for cmd in cmd_names]
        cmd_fns = filter(lambda x: hasattr(x, 'shortcut'), cmd_fns)
        return dict([(cmd.shortcut, cmd.__name__.split('_')[1])
                     for cmd in cmd_fns])

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
            lines = fh.readlines()
            fh.close()
            data = dict([line.split('=') for line in lines])
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

    def precmd(self, line):
        parts = line.split(' ', 1)
        cmd = parts[0]
        rest = parts[1:]
        if cmd in self.shortcuts.keys():
            return "%s %s" % (self.shortcuts[cmd], ''.join(rest))
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
            if len(output) > 10:
                pager('\n'.join(output))
            else:
                for line in output:
                    print line
        else:
            print "Query returned no results"
    do_query.trac_method = 'ticket.query'
    do_query.shortcut = 'q'

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
            if len(output) > 10:
                pager('\n'.join(output))
            else:
                print '\n'.join(output)
        else:
            print "Ticket %s not found" % ticket_id
    do_view.trac_method = 'ticket.get'
    do_view.shortcut = 'v'

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
            if len(output) > 10:
                pager('\n'.join(output))
            else:
                print '\n'.join(output)
    do_changelog.trac_method = 'ticket.changeLog'
    do_changelog.shortcut = 'log'

    def do_create(self, param_str):
        """
        Create and submit a new ticket to Trac instance

        trac->> create `title` `desc` `type` ...

        This feature works but is still under development.
        Please report any bugs you find.

        Shortcut: c

        Arguments:
        - `summary`: Title of the ticket
        """
        # would like to launch a blank template tmp file
        # and parse the returned file
        try:
            fname = tempfile.mktemp()
            fh = open(fname, "w")
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
    do_create.shortcut = 'c'

    def do_edit(self, ticket_id):
        """
        Edit a ticket in Trac

        trac->> edit `ticket_id` `field_query`

        This feature is still under development.
        Please report any bugs you find.

        Shortcut: e
        
        Arguments:
        - `ticket_id`: the id of the ticket to edit
        """

        try:
            ticket = self.trac.get_ticket(int(ticket_id))
        except ValueError:
            print "Invalid ticket id specified."
            return

        if ticket:
            (id, created, modified, orig_data) = ticket
            orig_data['comment'] = "Your comment here"
            lines = ['%s=%s\n' % (k, v.rstrip())
                     for k, v in orig_data.iteritems()]
            data = self._edit_ticket(lines)
            if data is None:
                return False
            if data.has_key('comment'):
                comment = data.pop('comment')
            else:
                comment = None
            # submit the difference between what went into the editor
            # and what came out
            orig_data.pop('comment') # we just popped it from data
            for k, v in orig_data.iteritems():
                if v in data[k]:
                    data.pop(k)
            self.trac.update_ticket(id, comment, data)
            print "Updated ticket %s: %s" % (id, comment)
        else:
            print "Ticket %s not found"
    do_edit.trac_method = 'ticket.update'
    do_edit.shortcut = 'e'

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
            data = self.parse_query_str(query_str)
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
        
    def parse_query_str(self, q):
        """
        Parse a query string

        Arguments:
        - `string`: A string in the form of field1=val field2="long val"
        """
        data = dict([item.split('=') for item in shlex.split(q)])
        return data

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
    do_quit.shortcut = 'Q'

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

    def help_shortcuts(self):
        text = """
        TracShell does have shortcuts for those inclined to
        save a few keystrokes. They are as follows:
        """
        print text
        for k, v in self.shortcuts.iteritems():
            print "%15s: %s" % (k, v)
