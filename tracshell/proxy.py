import os
import sys
import xmlrpclib as xmlrpc

from tracshell.backends import trac
from tracshell.helpers import dict_to_tuple

class ConnectionFailed(Exception): pass
class CallFailed(Exception): pass
class ValidationError(Exception): pass

class XMLRPCBase(object):
    """
    This base class acts as a wrapper around xmlrpclib and handles the
    connection and gathers the method list and method documentaion from
    the server.

    It is meant to be specialized by subclasses for use with particular
    XML-RPC servers.
    """

    def __init__(self, user, passwd, host,
                 port=80, path='/xmlrpc', secure=False):
        self._user = user
        self._passwd = passwd
        self._host = host
        self._port = port
        self._path = path
        self._protocol = 'https:' if secure else 'http:'

        # TODO: add proper SSL handling
        self._url = "%s//%s:%s@%s:%s%s" % (self._protocol,
                                           self._user,
                                           self._passwd,
                                           self._host,
                                           self._port,
                                           self._path)
        try:
            self.proxy = xmlrpc.ServerProxy(self._url)
        except xmlrpc.ProtocolError, e:
            raise ConnectionFailed("Error %s: %s" % (e.errcode, e.errmsg))
        else:
            # if the connection was successful
            # gather method names and documentation
            method_names = self.proxy.system.listMethods()
            method_help = list()
            multicall = xmlrpc.MultiCall(self.proxy)
            for name in method_names:
                multicall.system.methodHelp(name)
            for help in multicall():
                method_help.append(help)
            self.methods = dict(zip(method_names, method_help))


class TracProxy(XMLRPCBase):
    """
    A concrete class for working with the Trac XML-RPC server

    The Trac XML-RPC server plugin can be found at:
        http://trac-hacks.org/wiki/XmlRpcPlugin
    """

    backend = trac

    def __init__(self, user, passwd, host,
                 port=80, path='/xmlrpc', secure=False):
        XMLRPCBase.__init__(self, user, passwd, host,
                            port, path, secure)

        ticket_components = ['resolution', 'milestone', 'severity',
                             'status', 'version', 'priority',
                             'type', 'component']
        ticket_component_values = list()
        multicall = xmlrpc.MultiCall(self.proxy)
        # TODO: find a way to compress this into an iterator
        multicall.ticket.resolution.getAll()
        multicall.ticket.milestone.getAll()
        multicall.ticket.severity.getAll()
        multicall.ticket.status.getAll()
        multicall.ticket.version.getAll()
        multicall.ticket.priority.getAll()
        multicall.ticket.type.getAll()
        multicall.ticket.component.getAll()
        for resp in multicall():
            ticket_component_values.append(resp)
        self.ticket_meta = dict(zip(ticket_components,
                                    ticket_component_values))

    def validate_fields(self, fields):
        """
        Validates a dict of ticket fields against the legal values in
        self.ticket_meta

        Raises a ValidationError exception with a descriptive message
        if it finds any errors
        """
        errors = []
        for k, v in fields.iteritems():
            if self.ticket_meta.has_key(k):
                if fields[k] != '' and \
                fields[k] not in self.ticket_meta[k]:
                    errors.append((k, v,
                                   self.ticket_meta[k]))
        if len(errors) > 0:
            warn = "The following fields contain invalid values:\n"
            err_str = ''.join(["%s: %s %r" % err for err in errors])
            raise ValidationError, warn + err_str

    def get_ticket(self, id):
        """ Returns a backends.trac.Ticket object from the server """
        try:
            data = self.proxy.ticket.get(id)
        except xmlrpc.Fault, e:
            raise CallFailed, "Code %s: %s" % (e.faultCode,
                                               e.faultString)
        else:
            return self.backend.Ticket(data)

    def create_ticket(self, summary, description, fields=None,
                      get_ticket=False):
        """
        Create a new ticket and return a ticket object if `get_ticket`
        is True, else just return the ticket id.
        """
        # Note: can probably shorten this w/ a multicall and return
        #       a ticket object by default.
        if summary and description:
            if fields:
                self.validate_fields(fields)
            else:
                fields = {}
            try:
                id = self.proxy.ticket.create(summary,
                                              description,
                                              fields,
                                              False)
            except xmlrpc.Fault, e:
                raise CallFailed, "Code %s: %s" % (e.faultCode,
                                                   e.faultString)
            else:
                if get_ticket:
                    return self.get_ticket(id)
                else:
                    return id
        else:
            raise ValueError, "summary and description are required"

    def save_ticket(self, ticket, comment='No comment'):
        """ Saves a ticket to the server. """
        fields = ticket.get_attrs()
        self.validate_fields(fields)
        try:
            self.proxy.ticket.update(ticket.id,
                                     comment,
                                     ticket.get_changes())
        except xmlrpc.Fault, e:
            raise CallFailed, "Code %s: %s" % (e.faultCode,
                                               e.faultString)
        else:
            ticket._Ticket__original_data = dict_to_tuple(fields)

    def query_tickets(self, query):
        """ Queries a server for tickets matching the query string """
        multicall = xmlrpc.MultiCall(self.proxy)
        try:
            ticket_ids = self.proxy.ticket.query(query)
        except xmlrpc.Fault, e:
            raise CallFailed, "Code %s: %s" % (e.faultCode,
                                               e.faultString)
        else:
            for id in ticket_ids:
                multicall.ticket.get(id)
            tickets = [self.backend.Ticket(data)
                       for data in multicall()]
            return tickets

    def get_changelog(self, ticket):
        """ Queries the server for a tickets' changelog """
        # Note this check is a backwards-compatible hack
        # technically we should only expect a ticket object
        if isinstance(ticket, self.backend.Ticket):
            return self.proxy.ticket.changeLog(ticket.id)
        else:
            return self.proxy.ticket.changeLog(ticket)

    def get_changelogs(self, tickets):
        """
        Queries the server for multiple changelogs

        Returns a dict of {ticket_id: log}
        """
        multicall = xmlrpc.MultiCall(self.proxy)
        for ticket in tickets:
            multicall.ticket.changeLog(ticket.id)
        ticket_ids = [ticket.id for ticket in tickets]
        logs = [log for log in multicall()]
        return dict(zip(ticket_ids, logs))
