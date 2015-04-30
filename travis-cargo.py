#!/usr/bin/env python
from __future__ import print_function
import travis_cargo

if __name__ == '__main__':
    print("""Preferred project is now:
   pip install git+https://github.com/huonw/travis-cargo.git --user $USER && export PATH=$HOME/.local/bin:$PATH
""")
    travis_cargo.main()
