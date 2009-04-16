import fcntl
import termios
import struct

def get_termsize(term):
    st_ioctl = fcntl.ioctl(term, termios.TIOCGWINSZ, '1234')
    termsize = struct.unpack('hh', st_ioctl)
    return termsize

def dict_to_tuple(dict):
    return tuple([(k, v) for k,v in dict.iteritems()])
