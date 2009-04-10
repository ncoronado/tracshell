import fcntl
import termios
import struct

def get_termsize(term):
    ioctl_s = fcntl.ioctl(term, termios.TIOCGWINSZ, '1234')
    termsize = struct.unpack('hh', ioctl_s)
    return termsize
