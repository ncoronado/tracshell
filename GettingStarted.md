# Getting Started with TracShell #

TracShell is in a very early phase of development and getting it up and running isn't user-friendly (yet). Here is a quick guide to get started.

## Requirements ##

To use TracShell, you first need to have the XML-RPC plugin installed on your Trac server. You can get that plugin at:

http://trac-hacks.org/wiki/XmlRpcPlugin

You also need PyYAML installed on your client machine:

`easy_install pyyaml`

## Installation ##

Because TracShell is so early in development, it is prone to rapid change as new features are added and bugs squashed. The best way to install it is from source so that you can keep up with the latest changes as they are released:

`svn checkout http://tracshell.googlecode.com/svn/trunk/ tracshell`

Then, make sure that ./tracshell/tracshell is in your $PYTHONPATH.

One way is to create a symbolic link in your _site-packages_:

`ln -s ./tracshell/tracshell /usr/lib/python2.6/site-packages/tracshell`

(Remember to substitute the `/usr/lib/pythonx.x` part with the path to your systems' site-packages directory. Sorry Windows users, support is still lacking on that platform.)

Afterwards, add a symbolic link to ./tracshell/bin/tracshell somewhere in your $PATH.

## Setup ##

Ok, the basic setup is done. Now, a more tricky part is to setup the YAML setting file. Create a ".tracshell" file in your home directory and it put the following:

```
default_site: mytrac
--- !Site
name: mytrac
user: myself
passwd: mypassword
host: trac.myserver.com
port: 443
path: /trac/login/xmlrpc
secure: True
```

Remember to adjust the settings values for your particular Trac installation.

The `default_site` setting allows you to specify a default Trac server to connect to when you start up TracShell. Further sites can be added by copy/pasting the `=== !Site` section and changing the variables for the other site. Then when you start-up TracShell you can choose which server to connect to by name on the command line.

## Usage ##

That's it, you're ready! just launch tracshell by typing `tracshell` in your console (or emacs buffer...).

If you want to connect another site other than the default you specified in your settings file, you can type `tracshell =s myothersite`.

Voila!

If you ever encounter a feature you wish you had or find a bug, feel free to come back here and file a ticket or post a patch if you're so inclined. Thanks for your interest in TracShell!