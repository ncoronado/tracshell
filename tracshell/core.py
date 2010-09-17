import os
import sys
from optparse import OptionParser

from tracshell import settings
from tracshell import shell

def run():
    """
    This function starts the main program.
    """
    p = OptionParser(version="TracShell: %f" % shell.VERSION)
    p.add_option("--site", "-s", dest="site",
                 action="store", type="string",
                 default=None, help="Optional site to connect to")
    p.add_option("--file", "-f", dest="file",
                 action="store", type="string",
                 default=".tracshell", help="Specify the name of your settings file")
    opts, args = p.parse_args()

    s = settings.Settings(filename=opts.file)
    if opts.site:
        try:
            setattr(s, 'site', s.sites[opts.site])
        except KeyError:
            try:
                print >> sys.stderr, "Invalid site, trying default '%s'" % \
                    (s.default_site)
                setattr(s, 'site', s.sites[s.default_site])
            except AttributeError:
                print >> sys.stderr, "No default site specified"
                print >> sys.stderr, "Please check your configuration file"
                sys.exit()
    else:
        try:
            setattr(s, 'site', s.sites[s.default_site])
        except AttributeError:
            print >> sys.stderr, "No default site specified"
            print >> sys.stderr, "Check your configuration or specify one."
            print >> sys.stderr, "Try: 'tracshell -h' for help"
            sys.exit()
    if hasattr(s, 'editor'):
        shell.start_shell(s)
    else:
        try:
            s.editor = os.environ['EDITOR']
        except KeyError:
            print >> sys.stderr, "Please specify an editor in your settings"
            print >> sys.stderr, "or set your EDITOR environment variable."
        else:
            shell.start_shell(s)
