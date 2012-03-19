===================
Cmd2 - A better cmd
===================

Cmd2 is an extension built around the excellent cmd module of the standard
library.  Cmd allows one to build simple custom shells using ``do_*`` methods,
taking care in particular of the REPL loop and the interactive help.  However,
no facility is given for parsing the argument line (do_* methods are passed the
rest of the line as a single string argument).

With Cmd2, ``do_*`` methods are type-annotated, either using Python 3's
function annotation syntax, or with an ad-hoc ``annotate`` decorator, allowing
the dispatcher to parse the argument list for them.

Example
=======

    #!/usr/bin/env python2
    from cmd2 import *
    class UI(Cmd2):
    
        # With Python 3, use do_print(line: str, *, repeat: int).
        # Non-annotated arguments default to str.
        @annotate(line=str, repeat=int)
        @kw_only("repeat")
        def do_print(line, repeat)
            """Print a given string; do it multiple times if -repeat N option
            is given."""
            for i in range(repeat):
                print(line)
    
        # *args can also be annotated.
        @annotate(nums=float)
        def do_double(*nums):
            "Print twice the numbers given."
            for num in nums:
                print(2 * num)
    
        # Do not parse the argument line for do_shell.
        @gets_raw
        def do_shell(line)
            "Evaluates the given line."
            eval(line)

Remarks
=======

The parsing is done in the following steps:
  - the input line is passed to the `split()` method (by default
    `shlex.split()`), and the result is bound to the argument list of the
    `do_*` method.
  - initial options (`--opt val`) are assigned to keyword-only arguments (which
    can be simulated in Python 2 using the `@kw_only` decorator).
  - each value bound to an argument annotated with a callable, either through
    `@annotate([arg=callable]*)`, or through Python 3's function annotation
    syntax (`f(arg[=default]: callable)`), is passed to it; however, this does
    not affect default values),
  - if `do_*` has an annotated `*args` argument, then each element
    of args / each value in kwargs is casted.
  - in theory, `**kwargs` are also parsed and cast but there is currently
    effectively no way to assign to them.

Cmd2 interacts imperfectly with decorated functions.  Currently, it follows the
`__wrapped__` attribute until finding a function that either doesn't have this
attribute or is decorated with `@use_my_annotations`, uses the signature and
the annotations of this function to create the argument list, which is then
passed to the wrapper function.  In particular, Cmd2 provides a `wraps`
function that works like the one provided in functools, but also sets the
`__wrapped__` attribute (as in Python 3.3 or higher).
