#!/usr/bin/env python
from __future__ import print_function

if __name__ == '__main__':
    print("""project layout was changed. Use one of the following instead:
- to invoke the script with `travis-cargo`:
    pip install git+https://github.com/huonw/travis-cargo.git --user $USER && export PATH=$HOME/.local/bin:$PATH

- to invoke the script with `./tc`:
    pip install git+https://github.com/huonw/travis-cargo.git --user $USER && ln -s $HOME/.local/bin/travis-cargo tc
""")
    exit(1)
