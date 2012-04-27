"""ParsedCmd - A Cmd with argument list parsing

Interpreters constructed with this class obey the same conventions as those
constructed with cmd.Cmd, except that `do_*' methods are passed parsed argument
lists, instead of the raw input, as long as the method has not been decorated
with @gets_raw.

The parsing is done in the following steps:
  - the input line is passed to the `split()' method (by default
    `shlex.split()'), and the result is bound to the argument list of the
    `do_*' method.
  - initial options (`-opt val') are assigned to keyword-only arguments (which
    can be simulated in Python 2 using the `@kw_only' decorator).
  - each value bound to an argument annotated with a callable, either through
    `@annotate([arg=callable]*)', or through Python 3's function annotation
    syntax (`f(arg[=default]: callable)'), is passed to it; however, this does
    not affect default values),
  - if `do_*' has an annotated `*args' argument, then each element
    of args / each value in kwargs is casted.
  - in theory, `**kwargs' are also parsed and cast but there is currently
    effectively no way to assign to them.

ParsedCmd interacts imperfectly with decorated functions.  Currently, it
follows the `__wrapped__` attribute until finding a function that either
doesn't have this attribute or is decorated with `@use_my_annotations`, uses
the signature and the annotations of this function to create the argument list,
which is then passed to the wrapper function.  In particular, ParsedCmd
provides a `wraps` function that works like the one provided in functools, but
also sets the `__wrapped__` attribute (as in Python 3.3 or higher).
"""

from __future__ import print_function
from collections import namedtuple
from cmd import Cmd
import functools
import inspect
import itertools
import shlex
import sys
import textwrap

__all__ = ["gets_raw", "use_my_annotations", "ParsedCmd", "boolean"]

if sys.version_info.major >= 3:
    __all__.append("basestring")

    getfullargspec = inspect.getfullargspec
    getcallargs = inspect.getcallargs

    def getannotations(func):
        return getfullargspec(func).annotations

    def getkwonly(func):
        kwonly = getfullargspec(func).kwonlydefaults
        return kwonly.copy() if kwonly else {}

    basestring = str

else:
    if sys.version_info.major < 2 or sys.version_info.minor < 6:
        raise Exception("Cmd2 requires Python >= 2.6.")
    __all__.extend(["wraps", "annotate", "kw_only"])

    def getannotations(func):
        return getattr(func, "func_annotations", {})

    def getkwonly(func):
        return getattr(func, "kw_only", {}).copy()

    def getfullargspec(func):
        """Imitate Python 3's inspect.getfullargspec"""
        args_, varargs, varkw, defaults_ = inspect.getargspec(func)
        kwonlydefaults = getkwonly(func)
        kwonlyargs = kwonlydefaults.keys()
        # remove kw-only args *and* corresponding defaults
        if kwonlyargs: # (then _defaults is not empty)
            args = args_[:-len(kwonlyargs)]
            defaults = []
            for arg, default in zip(args_[-len(defaults_):], defaults_):
                if arg not in kwonlyargs:
                    args.append(arg)
                    defaults.append(default)
        else: # avoiding args_[:-0]
            args = args_
            defaults = defaults_
        annotations = getannotations(func)
        FullArgSpec = namedtuple("FullArgSpec",
            ("args", "varargs", "varkw", "defaults",
             "kwonlyargs", "kwonlydefaults", "annotations"))
        return FullArgSpec(args, varargs, varkw, defaults,
                           kwonlyargs, kwonlydefaults, annotations)

    # modified from Python 3's inspect module to handle kwonly arguments.
    def getcallargs(func, *positional, **named):
        """Get the mapping of arguments to values.

        A dict is returned, with keys the function argument names (including
        the names of the * and ** arguments, if any), and values the respective
        bound values from 'positional' and 'named'."""
        spec = getfullargspec(func)
        args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, ann = spec
        f_name = func.__name__
        arg2value = {}

        if inspect.ismethod(func) and func.__self__ is not None:
            # implicit 'self' (or 'cls' for classmethods) argument
            positional = (func.__self__,) + positional
        num_pos = len(positional)
        num_total = num_pos + len(named)
        num_args = len(args)
        num_defaults = len(defaults) if defaults else 0
        for arg, value in zip(args, positional):
            arg2value[arg] = value
        if varargs:
            if num_pos > num_args:
                arg2value[varargs] = positional[-(num_pos-num_args):]
            else:
                arg2value[varargs] = ()
        elif 0 < num_args < num_pos:
            raise TypeError('%s() takes %s %d positional %s (%d given)' % (
                f_name, 'at most' if defaults else 'exactly', num_args,
                'arguments' if num_args > 1 else 'argument', num_total))
        elif num_args == 0 and num_total:
            if varkw or kwonlyargs:
                if num_pos:
                    # XXX: We should use num_pos, but Python also uses num_total:
                    raise TypeError('%s() takes exactly 0 positional arguments '
                                    '(%d given)' % (f_name, num_total))
            else:
                raise TypeError('%s() takes no arguments (%d given)' %
                                (f_name, num_total))

        for arg in itertools.chain(args, kwonlyargs):
            if arg in named:
                if arg in arg2value:
                    raise TypeError("%s() got multiple values for keyword "
                                    "argument '%s'" % (f_name, arg))
                else:
                    arg2value[arg] = named.pop(arg)
        for kwonlyarg in kwonlyargs:
            if kwonlyarg not in arg2value:
                try:
                    arg2value[kwonlyarg] = kwonlydefaults[kwonlyarg]
                except KeyError:
                    raise TypeError("%s() needs keyword-only argument %s" %
                                    (f_name, kwonlyarg))
        if defaults:    # fill in any missing values with the defaults
            for arg, value in zip(args[-num_defaults:], defaults):
                if arg not in arg2value:
                    arg2value[arg] = value
        if varkw:
            arg2value[varkw] = named
        elif named:
            unexpected = next(iter(named))
            raise TypeError("%s() got an unexpected keyword argument '%s'" %
                            (f_name, unexpected))
        unassigned = num_args - len([arg for arg in args if arg in arg2value])
        if unassigned:
            num_required = num_args - num_defaults
            raise TypeError('%s() takes %s %d %s (%d given)' % (
                f_name, 'at least' if defaults else 'exactly', num_required,
                'arguments' if num_required > 1 else 'argument', num_total))
        return arg2value

    def annotate(**kwargs):
        """Decorator factory to simulate Python 3's annotation mechanism."""
        def decorator(func):
            argspec = getfullargspec(func)
            for kw in kwargs:
                if (kw not in argspec.args and
                    kw not in argspec.kwonlyargs and
                    kw not in [argspec.varargs, argspec.varkw, "return"]):
                    raise Exception(
                        "Invalid annotation ({0}={1}) for function {2}.".
                        format(kw, kwargs[kw], func.__name__))
            func.func_annotations = kwargs
            return func
        return decorator

    def kw_only(*args):
        """Decorator factory to simulate Python 3's kw-only arguments without
        actually enforcing it."""
        def decorator(func):
            argspec = getfullargspec(func)
            kw_args = (argspec.args[-len(argspec.defaults):]
                       if argspec.defaults else [])
            for kw in args:
                if kw not in kw_args:
                    raise Exception(
                        "Invalid kw-only annotation of argument {0} for "
                        "function {1}".format(kw, func.__name__))
            func.kw_only = dict((kw, argspec.defaults[kw_args.index(kw)])
                                for kw in args)
            return func
        return decorator

    def wraps(func):
        """Decorator factory that calls functools.wraps and also sets the
        __wrapped__ attribute.
        """
        def wrapper_decorator(wrapper):
            decorated_wrapper = functools.wraps(func)(wrapper)
            decorated_wrapper.__wrapped__ = func
            return decorated_wrapper
        return wrapper_decorator

GETS_RAW = "_gets_raw"
def gets_raw(func):
    """Decorator indicating that the do_* method requires an unparsed line."""
    setattr(func, GETS_RAW, True)
    return func

USE_MY_ANNOTATIONS = "_use_my_annotations"
def use_my_annotations(func):
    """Decorator indicating that the annotations of the decorated method should
    be used.
    """
    setattr(func, USE_MY_ANNOTATIONS, True)
    return func

class ArgListError(Exception):
    """The argument list to the dispatched method could not be constructed."""
    pass

class ParsedCmd(Cmd, object):
    """An subclass of cmd.Cmd that can parse arguments."""

    def onecmd(self, line):
        # initial parsing
        cmd, arg, line = self.parseline(line)
        if not line:
            return self.emptyline()
        if cmd is None:
            return self.default(line)
        self.lastcmd = line
        # find the method to which dispatch
        if cmd == "":
            return self.default(line)
        try:
            func = getattr(self, "do_" + cmd)
        except AttributeError:
            return self.default(line)
        inner_func = func
        while (hasattr(inner_func, "__wrapped__") and
               not getattr(inner_func, USE_MY_ANNOTATIONS, None)):
            inner_func = inner_func.__wrapped__
        try:
            args, kwargs = self.construct_arglist(arg, func, inner_func)
        except ArgListError as exc:
            callback, args = exc.args
            return callback(*args)
        return func(*args, **kwargs)
    onecmd.__doc__ = Cmd.onecmd.__doc__

    def split(self, line):
        """Split the argument list."""
        return [arg.replace("\0", "") for arg in shlex.split(line)]

    def construct_arglist(self, arg, func, inner_func):
        """Construct *args and **kwargs to be passed to func from arg and
        inner_func's signature.
        """
        if getattr(inner_func, GETS_RAW, None):
            return [arg], {}
        args = self.split(arg)
        argspec = getfullargspec(inner_func)
        kw_args = (argspec.args[-len(argspec.defaults):]
                   if argspec.defaults else [])
        kw_only = getkwonly(inner_func)
        # args = ["--kw", opt, "--kw", opt, ..., val, val...]
        # -> args = [val, val, ...]
        # -> opts = {"kw": opt, "kw": opt, ...}
        while args and isinstance(args[0], basestring):
            kw = args[0].lstrip("-")
            if kw in kw_only:
                try:
                    kw_only[kw] = args[1]
                except IndexError:
                    exc_s = "Value not given for option."
                    raise ArgListError(self.bind_error, (args, exc_s))
                args = args[2:]
            else:
                break
        if not inspect.ismethod(inner_func):
            args.insert(0, self)
        try:
            callargs = getcallargs(inner_func, *args, **kw_only)
        except TypeError as exc:
            exc_s = str(exc)
            raise ArgListError(self.bind_error, (args, exc_s))
        for varname in callargs:
            cast = argspec.annotations.get(varname)
            if not callable(cast):
                continue
            bound_val = callargs[varname]
            if varname == argspec.varargs:
                bound_val = list(bound_val)
                for i, arg in enumerate(bound_val):
                    try:
                        bound_val[i] = cast(arg)
                    except Exception as exc:
                        exc_s = str(exc)
                        raise ArgListError(self.cast_error,
                                           (varname, arg, cast, exc_s))
                callargs[varname] = bound_val
            elif varname == argspec.varkw:
                for key, val in bound_val.items():
                    try:
                        bound_val[key] = cast(val)
                    except Exception as exc:
                        exc_s = str(exc)
                        raise ArgListError(self.cast_error,
                                           (varname, arg, cast, exc_s))
            elif (bound_val ==
                  getattr(argspec, "kwonlydefaults", {}).get(varname, object())):
                continue # same as given default, keyword-only
            elif (varname in kw_args and
                  bound_val == argspec.defaults[kw_args.index(varname)]):
                continue # same as given default, non-keyword-only
            else:
                try:
                    callargs[varname] = cast(bound_val)
                except Exception as exc:
                    exc_s = str(exc)
                    raise ArgListError(self.cast_error,
                                       (varname, bound_val, cast, exc_s))
        # reconstruct the argument list
        args = [callargs[varname]
                for varname in argspec.args if varname not in kw_args]
        if argspec.varargs:
            args.extend(callargs[argspec.varargs])
        kwargs = dict((varname, callargs[varname])
                      for varname in kw_args + argspec.kwonlyargs)
        if argspec.varkw:
            kwargs.update(argspec.varkw)
        if inspect.ismethod(func):
            return args[1:], kwargs
        else:
            return args, kwargs

    def bind_error(self, args, exc):
        """Called when the argument list does not match the method's
        signature."""
        print("*** This argument list could not be bound:", args)
        print("***", exc)

    def cast_error(self, varname, value, cast, exc):
        """Called when an argument cannot be cast by the given caster."""
        print(textwrap.fill('*** While trying to cast "{0}" with "{1}" for '
                            'argument "{2}", the following exception was '
                            'thrown:'.format(value, cast, varname),
                            72, subsequent_indent="*** "))
        print("***", exc)

    def do_help(self, cmd=None):
        return Cmd.do_help(self, cmd)

def boolean(s):
    """A generalized boolean caster."""
    return s.lower() not in ["off", "false", "f", "0"]
