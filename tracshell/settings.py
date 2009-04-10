import os
import sys

try:
    import yaml
except ImportError:
    print >> sys.stderr, "TracShell requires PyYAML to be installed."
    sys.exit()

class ConfigError(Exception): pass

# PyYAML note: While the documentation about YAMLObject gives an example with
# __init__, the issue 48, at http://pyyaml.org/ticket/48, reveals that
# __init__ is in fact never called. I thus removed the __init__ methods.

class Site(yaml.YAMLObject):
    """
    This class stores information for connecting to a Trac instance.
    """
    yaml_tag = u'!Site'

class Settings(object):

    valid_settings = ['editor', 'default_site', 'aliases']

    def __init__(self, filename='.tracshell'):
        filename = os.path.join(os.path.expanduser('~'), filename)
        self.sites = {}
        self.aliases = {}
        
        try:
            yaml_objects = yaml.load_all(open(filename))
        except yaml.YAMLError, e:
            print >> sys.stderr, "Error parsing settings file: %s" % e
        else:
            self._parse_settings(yaml_objects)
    
    def _parse_rest(self, yaml_object):
        if isinstance(yaml_object, dict):
            for k, v in yaml_object.items():
                if k in self.valid_settings:
                    setattr(self, k, v)
                else:
                    raise ConfigError("Invalid config option: %s" % k)
    
    def _parse_site(self, site):
        self.sites[site.name] = site
    
    def _parse_settings(self, yaml_objects):
        for yaml_object in yaml_objects:
            if isinstance(yaml_object, Site):
                self._parse_site(yaml_object)
            else:
                self._parse_rest(yaml_object)
