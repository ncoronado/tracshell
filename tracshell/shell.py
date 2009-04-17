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
from tracshell.proxy import TracProxy, ValidationError, CallFailed

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

def start_shell(settings):
    """
    start_shell is a constructor class for building TracShell instances.

    Arguments:
    - `settings`: a configured tracshell.settings.Settings object
                  with a 'site' attribute set with the
                  tracshell.settings.Site object set for the site
                  to connect to.
    """
    trac = TracProxy(settings.site.user,
                     settings.site.passwd,
                     settings.site.host,
                     settings.site.port,
                     settings.site.path,
                     settings.site.secure)
    if settings.editor is None or settings.editor == '':
        print >> sys.stderr, "Warning, no editor set."
    shell = TracShell(trac, settings.editor)
    server_methods = trac.methods.keys()
    shell_methods = [getattr(shell, x) for x in dir(shell)
        if x.startswith('do_')]
    shell_methods = [x for x in shell_methods if hasattr(x, 'trac_method')]
    for method in shell_methods:
        if method.trac_method not in server_methods:
            delattr(shell, method.__name__)
    shell.cmdloop()

class TracShell(cmd.Cmd):
    """
    TracShell is a shell interface to a Trac instance.
    
    It uses and XML-RPC interface to Trac provided by:

        http://trac-hacks.org/wiki/XmlRpcPlugin#DownloadandSource
    """

    def __init__(self, trac_interface, editor):
        """ Initialize the XML-RPC interface to a Trac instance.

        Arguments:
        - `trac_interface`: an initialized tracshell.trac.Trac instance
        - `editor`: a path to a valid editor
        """
        self._editor = editor
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
        except (AttributeError, OSError):
            print "No editor set. Can't continue"
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
            matches = re.findall(field_pattern, content,
                                 re.DOTALL | re.MULTILINE)
            data = dict([(f, v.strip()) for f, v in matches])
            return data
        except ValueError, e:
            print "Something went wrong or the file was formatted"
            print "wrong. Please try submitting the ticket again"
            print "or file a bug report with the TracShell devs."
            print "Error: %s" % unicode(e)
            return None
    
    def _parse_query_str(self, q):
        """
        Parse a query string

        Arguments:
        - `string`: A string in the form of field1=val field2="long val"
        """
        data = dict([item.split('=') for item in shlex.split(q)])
        return data
    
    def _print_output(self, output_lines):
        output = '\n'.join(output_lines)
        if getattr(settings, 'pager', False) and len(output) > TERM_SIZE[0]:
            pager(output)
        else:
            print output
    
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
        try:
            tickets = self.trac.query_tickets('&'.join(shlex.split(query)))
        except CallFailed:
            print >> sys.stderr, "Bad query specified, please see `help queries`"
        else:
            output = []
            if tickets:
                for ticket in tickets:
                    output.append("%5s: [%s] %s" % (ticket.id,
                                                    ticket.status.center(8),
                                                    ticket.summary))
                self._print_output(output)
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
            data = ticket.get_attrs()
            data['created'] = ticket.created
            data['last_modified'] = ticket.modified

            output.append("Details for Ticket: %s" % ticket.id)
            for k, v in data.iteritems():
                output.append("%15s: %s" % (k, v))
            self._print_output(output)
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
            changes = self.trac.get_changelog(int(ticket_id))
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
            self._print_output(output)
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
                              "reporter=%s\n" % self.trac._user,
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
                                             fields=data)
            except ValidationError, e:
                print e
                return False
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
        if changes is None: # Summon the editor
            orig_data = ticket.get_attrs()
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
                    del(data[k])
        else: # just do the update
            data = self._parse_query_str(changes)
        if 'comment' in data:
            comment = data.pop('comment')
        else:
            comment = ''
        for k, v in data.iteritems():
            setattr(ticket, k, v)
        self.trac.save_ticket(ticket, comment)
        print "Updated ticket %s: %s" % (ticket.id, comment)
    
    do_edit.trac_method = 'ticket.update'
    
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
    
    def help_aliases(self):
        text = "Here is the list of the currently defined aliases:"
        print text
        for k, v in self.aliases.items():
            print "%15s: %s" % (k, v)
    
