#!/usr/bin/env python
from __future__ import print_function

if __name__ == '__main__':
    print("""project layout was changed. Use the following instead:

    pip install 'travis-cargo<0.2' --user && export PATH=$HOME/.local/bin:$PATH

See these links for more info:
- https://github.com/huonw/travis-cargo
- http://huonw.github.io/blog/2015/05/travis-on-the-train-part-2/#breaking-change
""")
    exit(1)
