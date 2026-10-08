import os

# The CLI's rich console is created when `btl.cli.app` is imported, and it reads FORCE_COLOR
# then: CLI output would be coloured and `replay` would think it runs in a terminal. Tests
# import the CLI at collection, after this file, so clearing the variable here is early enough.
os.environ.pop("FORCE_COLOR", None)
