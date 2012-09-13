import sys

sys.path.append(".")
if sys.version_info[0] == 2:
    from _test_py2 import *
else:
    from _test_py3 import *
