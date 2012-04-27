from io import StringIO
from parsedcmd import *

class UI(ParsedCmd):
    def do_print(self, line="abc", *, repeat: int=1):
        """Return a given string (defaults to "abc"); return multiple copies if
        -repeat N option is given."""
        for i in range(repeat):
            print(line, file=self.stdout)

    def do_double(self, *nums: int, flag: boolean=True):
        "Print twice the numbers given, except if -flag is set to false."
        if flag:
            for num in nums:
                print(2 * num, file=self.stdout)

    @gets_raw
    def do_shell(self, line):
        "Evaluates the given line."
        eval(line)

class Tests:
    def setUp(self):
        self.out = StringIO()
        self.ui = UI(stdout=self.out)

    def test_print(self):
        self.ui.onecmd("print")
        assert self.out.getvalue().strip() == "abc"

    def test_print_repeat(self):
        self.ui.onecmd("print -repeat 3 def")
        assert self.out.getvalue().strip() == "def\ndef\ndef"

    def test_print_flag(self):
        self.ui.onecmd("print -flag off -repeat 3 def")
        assert self.out.getvalue().strip() == ""

    def test_double(self):
        self.ui.onecmd("double 1 2 3")
        assert self.out.getvalue().strip() == "2\n4\n6"

    def test_shell(self):
        self.ui.onecmd("!print(1, file=self.stdout)")
        assert self.out.getvalue().strip() == "1"

if __name__ == "__main__":
    UI().cmdloop()
