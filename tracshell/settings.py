import os
import sys

import yaml

class ConfigError(Exception): pass

class TracSite(yaml.YAMLObject):
    """
    This class stores information for connecting to a Trac instance.
    """

    yaml_tag = u'!TracSite'

    def __init__(self, name, user, passwd, host, port, path, secure=False):
        self.name = name
        self.user = user
        self.passwd = passwd
        self.host = host
        self.port = port
        self.path = path
        self.secure = secure


class Settings(object):

    valid_settings = ['editor']

    def __init__(self, file='.tracshell'):
        self.file = os.path.join(os.path.expanduser('~'), file)
        self.sites = dict()
        
        try:
            self._settings = yaml.load_all(open(self.file))
        except yaml.YAMLError, e:
            print >> sys.stderr, "Error parsing settings file: %s" % e
        else:
            self._parse_settings(self._settings)

    def _parse_settings(self, settings):
        for setting in settings:
            if isinstance(setting, TracSite):
                self.sites[setting.name] = setting
            else:
                if isinstance(setting, dict):
                    print setting
                    for k,v in setting.iteritems():
                        if k in self.valid_settings:
                            setattr(self, k, v)
                        else:
                            raise ConfigError, "Invalid config option: %s" % k
                else:
                    pass
                            
