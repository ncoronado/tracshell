import os
import sys

from tracshell.helpers import dict_to_tuple

class Ticket(object):
    """
    A class that represents a Trac ticket
    """

    def __get_id(self):
        return self.__id

    def __get_created(self):
        return self.__created

    def __get_modified(self):
        return self.__modified

    def __get_original(self):
        return self.__original_data

    id = property(fget=__get_id)
    created = property(fget=__get_created)
    modified = property(fget=__get_modified)
    original_data = property(fget=__get_original)

    def __init__(self, data):
        """
        Arguments:
        - `data`: an object returned by the ticket.get
                  XML-RPC call or a dictionary of attributes
        """
        self.__id = data[0] if isinstance(data, list) else None
        self.__created = data[1] if isinstance(data, list) else None
        self.__modified = data[2] if isinstance(data, list) else None
        # this is kind of ugly here, but prevents mod'ing
        # original_data -- a dict is still mutable and property()
        # doesn't appear to protect it.
        if isinstance(data, list):
            self.__original_data = dict_to_tuple(data[3])
            for k, v in data[3].iteritems():
                setattr(self, k, v)
        else:
            for k, v in data.iteritems():
                setattr(self, k, v)

    def __str__(self):
        return "<Ticket #%s>" % self.id

    def __repr__(self):
        attrs = [k for k in self.__dict__.keys()
                 if not k.startswith('_') and
                 k not in ['id', 'created', 'modified']]
        vals = list()
        for k in attrs:
            vals.append(getattr(self, k))
        properties = dict(zip(attrs, vals))
        return "Ticket([%d, %r, %r, %r])" % (self.id,
                                             self.created,
                                             self.modified,
                                             properties)

    def get_attrs(self):
        """ Returns a dict of instance attributes """
        return dict([(attr, getattr(self, attr)) for
                     attr in dict(self.original_data).keys()])

    def get_changes(self):
        """
        Compares the original data from the server to the instance
        attributes and returns a dict with only the values which
        differ between the instance and the original data.
        """
        original_dict = dict(self.original_data)
        attrs = original_dict.keys()
        new_data = {}
        diff = {}
        for attr in attrs:
            new_data[attr] = getattr(self, attr)
        for k, v in original_dict.iteritems():
            if original_dict[k] != new_data[k]:
                diff[k] = new_data[k]
        return diff
