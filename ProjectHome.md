A command line shell interface to remote Trac instances using the Trac XML-RPC plugin. (available at: http://trac-hacks.org/wiki/XmlRpcPlugin).

To get up and running with TracShell, check out the GettingStarted wiki page.

TracShell allows you to get away from the browser and work with Trac servers in a shell or emacs buffer. With it you can:

```
# to query Trac for tickets...
trac->> query owner=bob priority=critical
   23: [  new  ] The house is on fire!
  233: [  open ] OMG aliens!
  256: [  new  ] Your guitar gets it unless you clean your room

# then we can  view a ticket by typing..
trac->> view 23
Details for ticket 23:

    Summary: The house is on fire!
     Status: New
     ...
```

This is still really early work. Probably like, alpha level. Which basically means the code is prone to rapid changes between individual revisions. As of [r10](https://code.google.com/p/tracshell/source/detail?r=10) or so, I've been using it for my day to day work, but it's still a work in progress. If you don't mind hacking your tools, then you might be comfortable with using TracShell at this stage (and maybe you could submit some patches?).

Ideas, suggestions, comments, and bug reports welcome. Anyone who finds this useful and wants to become a contributor is free to apply.