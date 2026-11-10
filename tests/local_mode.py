"""Explicit compatibility harness for pre-startup component CLI tests.

Verified-startup integration tests call casf.cli.main directly.
"""

from casf.cli import main


def local_cli(args):
    writing = args and (args[0] in {"init", "append", "checkpoint", "seal"}
                       or args[:2] == ["witness", "submit"])
    if writing and "--local-only" not in args:
        args = [*args, "--local-only"]
    return main(args)
