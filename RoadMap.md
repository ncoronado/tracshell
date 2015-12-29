#Where TracShell should be before it's useful to the general populace

# Introduction #

tracshell is still very early in its development and will probably still undergo some rapid evolution before the code-base will mellow out and become what I like to think of as "stable."

I'm still writing a bit of prototyping code here and there to try out new design ideas as I explore my use of this tool as it evolves. After a few weeks of using it at work, I think I've got a solid understanding of where to take it before I put the magic 1.0.0 marker on it.


# Details #

## Building a Dynamic Shell Interface ##

Trac users have varying permissions on any instance which tracshell currently doesn't understand. In my use of tracshell in my daily work I've discovered that it's important to know what commands are available to a user.

I've concluded that the best way to approach the problem is to find a way to dynamically generate available shell commands based on which commands are available on the server.

The benefit I hope is obvious. It avoids the possibility of running into the useless, "You do not have permission to perform this action" type of error message which is just frustrating ("You mean I spent all that time typing in that information for nothing? Now what?"). If a user cannot perform a command in the shell, it shouldn't even appear in the shell.

## Smart Exception Handling ##

XML-RPC calls are untrustworthy and rife with innumerable side-effects. You can never trust that an XML-RPC call will succeed or even return anything, let alone the data you were expecting in the first place.

tracshell will need a more reliable and consistent way of handling this concept.

In the case that something does go wrong, the user shouldn't get a blanket statement from the program. It should be as specific as it can so that at least there is assurance the problem can be solved; either by the user or by the developers.

## Interface Enhancements ##

While the cmd.Cmd module does a great job, it will need a little more to go the extra mile. Short commands just came up in the issue tracker and I think that's a good idea. Other enhancements will be needed beyond tab-completion and command history. Short commands are a start, but I think 1.0.0 will also need to store configurations, be able to output data to disk, and have user-configurable output formatting.