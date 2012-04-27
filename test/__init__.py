import sys as _sys

if _sys.version_info[0] == 2:
    from . import test_py2
else:
    from . import test_py3
