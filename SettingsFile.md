The Tracshell settings file is a YAML file. When starting Tracshell, you can specify a settings file to load, but the default settings file is ~/.tracshell. Here is a sample settings file:

```
editor: /usr/bin/vi
default_site: mysite
aliases:
    current: query status!=closed milestone="current milestone"
    mine: query status=assigned owner=username
    fix: edit $1 status=closed resolution=fixed comment="$0"

---
!Site
name: mysite
user: username
passwd: password
host: trac.mysite.com
port: 80
path: /login/xmlrpc
secure: false
```

# Site #

For Tracshell to work correctly, you need to define at least one site and also set `default_site` to one of your site. The site's settings themselves are pretty straightforward, just look at the example above to get an idea of what to write in there.


# Aliases #

You can create aliases for commands you often use, such as seeing open tickets, or fixing a ticket. To define aliases, add an `alias` mapping element, and for each alias, add a sub-mapping element in the form of `alias_name --> command`.

If you want, you can also add arguments to your aliases (`$1` means the first argument, `$2`, the second, and `$0` collects all remaining arguments. arguments are space-separated). For example, if you define an alias as `fix: edit $1 status=closed resolution=fixed comment="$0"`, typing `fix 42 killed some nasty bug` will be equivalent to typing `edit 42 status=closed resolution=fixed comment="killed some nasty bug"`.