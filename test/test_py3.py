from io import StringIO
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

class Tests:
    def setup(self):
        self.out = StringIO()
        self.ui = UI(stdout=self.out, show_usage=True)

    def test_print(self):
        self.ui.onecmd("print")
        assert self.out.getvalue().strip() == "abc"

    def test_print_repeat(self):
        self.ui.onecmd("print -repeat 3 def")
        assert self.out.getvalue().strip() == "def\ndef\ndef"

    def test_print_flag(self):
        self.ui.onecmd("print -flag off -repeat 3 def")
        assert self.out.getvalue().strip() == ""

    def test_help_print(self):
        self.ui.onecmd("help print")
        assert (self.out.getvalue().strip() ==
                UI.do_print.__doc__ +
                "\n\tprint [-flag F(=True)] [-repeat R(=1)] [LINE(=abc)]")

    def test_multiply(self):
        self.ui.onecmd("multiply 4 1 2 3")
        assert self.out.getvalue().strip() == "4\n8\n12"

    def test_help_multiply(self):
        self.ui.onecmd("?multiply")
        assert (self.out.getvalue().strip() ==
                UI.do_multiply.__doc__ + "\n\tmultiply MUL [NUMS]")

    def test_shell(self):
        self.ui.onecmd("!print(1, file=self.stdout)")
        assert self.out.getvalue().strip() == "1"

if __name__ == "__main__":
    UI(show_usage=True).cmdloop()
