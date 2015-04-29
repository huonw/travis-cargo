# travis-cargo

This provides a standalone script `travis-cargo.py` that manages
running cargo as appropriate for different versions of Rust, and
incorporates the documentation upload technique
[described by hoverbear][hoverbear] with
[my modifications to avoid `sudo`][nosudo] (in particular, it requires
[an encypted `GH_TOKEN`][ghtoken]).

[hoverbear]: http://www.hoverbear.org/2015/03/07/rust-travis-github-pages/
[nosudo]: http://huonw.github.io/blog/2015/04/little-libraries/#the-process
[ghtoken]: http://www.hoverbear.org/2015/03/07/rust-travis-github-pages/#givingtravispermissions

The script is designed to automatically work with both Python 2 and
Python 3.

Help:

```
usage: travis-cargo.py [-h] [-q] [--only VERSION] {cargo,doc-upload} ...

manages interactions between travis and cargo/rust compilers

optional arguments:
  -h, --help          show this help message and exit
  -q, --quiet         don't pass --verbose to cargo
  --only VERSION      only run the given command if the specified version
                      matches `TRAVIS_RUST_VERSION`

subcommands:
  {cargo,doc-upload}
    cargo             run cargo, passing `--features
                      $TRAVIS_CARGO_NIGHTLY_FEATURE` (default 'unstable') if
                      the nightly branch is detected, and skipping `cargo
                      bench` if it is not
    doc-upload        uses ghp-import to upload cargo-rendered docs from the
                      master branch
```

## Example

A possible configuration is:

```yaml
language: rust
# run builds for both the nightly and beta branch
rust:
  - nightly
  - beta

# load travis-cargo
before_script:
  - git clone --depth 1 https://github.com/huonw/travis-cargo
  # make a short alias (`alias` itself doesn't work)
  - ln -s ./travis-cargo/travis-cargo.py tc

# the main build
script:
  - |
      ./tc cargo build &&
      ./tc cargo test &&
      ./tc cargo bench &&
      ./tc --only beta cargo doc
after_success:
  # upload the documentation from the build with beta (automatically only actually
  # runs on the master branch)
  - ./tc --only beta doc-upload

env:
  global:
    # override the default `--features unstable` used for the nightly branch (optional)
    - TRAVIS_CARGO_NIGHTLY_FEATURE=nightly
    # encrypted github token for doc upload (see `GH_TOKEN` link above)
    - secure: "..."
```

Extra arguments can be passed to `cargo` invocations, although
`-`-prefixed arguments will need to occur after a `--`, e.g. `tc cargo
build -- --features something`.
