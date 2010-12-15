import fcntl
import termios
import struct

from functools import wraps


def get_termsize(term):
    st_ioctl = fcntl.ioctl(term, termios.TIOCGWINSZ, '1234')
    termsize = struct.unpack('hh', st_ioctl)
    return termsize

def dict_to_tuple(dict):
    return tuple([(k, v) for k,v in dict.iteritems()])

def shell_command(cmd_name): 
    """ Return a wrapped function with a `trac_method` attribute set
    to the value of `cmd_name`.

    Arguments:
    - `cmd_name`: Should be a string value that maps to a Trac XML-RPC
                  method
    """
    def inner(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func.trac_method = cmd_name
            return func(*args, **kwargs)
        return wrapper
    return inner
