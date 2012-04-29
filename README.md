ParsedCmd - A Cmd with argument list parsing
============================================

ParsedCmd is an extension built around the excellent cmd module of the standard
library.  Cmd allows one to build simple custom shells using ``do_*`` methods,
taking care in particular of the REPL loop and the interactive help.  However,
no facility is given for parsing the argument line (`do_*` methods are passed
the rest of the line as a single string argument).

With ParsedCmd, ``do_*`` methods can be type-annotated, either using Python 3's
function annotation syntax, or with the ad-hoc ``annotate`` decorator, allowing
the dispatcher to parse the argument list for them.  Arguments can also be
marked as keyword-only, either using Python 3's dedicated syntax, or with the
ad-hoc ``kw_only`` decorator, in which case they will be assigned only if given
as explicit arguments, i.e. ``method -option opt`` translates into
``do_method(option=opt)`` if ``option`` is keyword-only.

These annotations can also used to enhance the output of the default `do_help`
method, by setting the `show_usage` attribute of the ParsedCmd object to True.

Example (Python 2)
==================

    from parsedcmd import *

    class UI(ParsedCmd):
        # Non-annotated arguments default to str.
        # boolean is a utility function, that casts every string to True,
        # except "f", "false", "off" and "0" (case-insensitive).
        @annotate(flag=boolean, repeat=int)
        @kw_only("flag", "repeat")
        def do_print(self, line="abc", flag=True, repeat=1):
            """Print a given string (defaults to "abc").
            Print nothing if -flag is set to false.
            Print multiple copies if -repeat N option is given.
            """
            if flag:
                for i in range(repeat):
                    print(line, file=self.stdout)

        # *args can also be annotated.
        # Python 2's usual limitations about mixing keyword arguments and *args
        # applies.
        @annotate(mul=int, nums=int)
        def do_multiply(self, mul, *nums):
            """Print `mul` times the numbers given.
            """
            for num in nums:
                print(mul * num, file=self.stdout)

        # Do not parse the argument line for do_shell.
        @gets_raw
        def do_shell(self, line):
            """Evaluates the given line.
            """
            eval(line)

Example (Python 3)
==================

    from parsedcmd import *

    class UI(ParsedCmd):
        def do_print(self, line="abc", *, flag: boolean=True, repeat: int=1):
            """Print a given string (defaults to "abc").
            Print nothing if -flag is set to false.
            Print multiple copies if -repeat N option is given.
            """
            if flag:
                for i in range(repeat):
                    print(line, file=self.stdout)

        def do_multiply(self, mul: int, *nums: int):
            """Print `mul` times the numbers given.
            """
            for num in nums:
                print(mul * num, file=self.stdout)

        @gets_raw
        def do_shell(self, line):
            """Evaluates the given line.
            """
            eval(line)

Remarks
=======

The parsing is done in the following steps:
  - the input line is passed to the `split()` method (by default
    `shlex.split()`), and the result is bound to the argument list of the
    `do_*` method.
  - initial options (`-opt val`) are assigned to keyword-only arguments (which
    can be simulated in Python 2 using the `@kw_only` decorator).
  - each value bound to an argument annotated with a callable, either through
    `@annotate([arg=callable]*)`, or through Python 3's function annotation
    syntax (`f(arg[=default]: callable)`), is passed to it; however, this does
    not affect default values),
  - if `do_*` has an annotated `*args` argument, then each element
    of args / each value in kwargs is casted.
  - in theory, `**kwargs` are also parsed and cast but there is currently
    effectively no way to assign to them.

ParsedCmd interacts imperfectly with decorated functions.  Currently, it
follows the `__wrapped__` attribute until finding a function that either
doesn't have this attribute or is decorated with `@use_my_annotations`, uses
the signature and the annotations of this function to create the argument list,
which is then passed to the wrapper function.  In particular, ParsedCmd
provides a `wraps` function that works like the one provided in functools, but
also sets the `__wrapped__` attribute (as in Python 3.3 or higher).
