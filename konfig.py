import os
import re


class Konfig:
    """Simple software configuration module.

    Example:
    from konfig import Konfig
    konf = Konfig()
    konf.username


    Callling "konf.username" will search
    the following locations and return the first value that is found:
    - An environment variable named "USERNAME" ($USERNAME in the shell)
    - If './.env' exists and has an entry that starts with "USERNAME="
    - If an entry in a dictionary was passed to "konf.use_dict()" before
      "konf.username" was called, that will be returned.
    """
    def __init__(self):
        self.kv = {}
        filename = '.env'
        if not os.path.isfile(filename):
            return
        for line in open(filename).readlines():
            match = re.match(r'\A([A-Za-z0-9_]+)=(.*)', line)
            if match:
                self.kv[match.group(1)] = str(match.group(2))

    def use_dict(self, input):
        for key in input.keys():
            self.kv[key] = str(input[key])

    def __getattr__(self, key):
        if key in self.kv:
            return self.kv[key]
        elif os.getenv(key.upper()):
            return os.getenv(key.upper())
        elif key.upper() in self.kv:
            return self.kv[key.upper()]
        else:
            return False
