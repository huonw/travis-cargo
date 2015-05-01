# travis-cargo

This provides a standalone script `travis-cargo` that manages
running cargo and several other related features on [Travis CI][travis].

[travis]: http://travis-ci.org

Features:

- run commands only on specific versions of the compiler
- insert a feature flag when using a nightly compiler to enable
  conditional use of unstable features
- automatically only run `cargo bench` when supported (nightly
  compiler)
- upload documentation via the technique
  [described by hoverbear][hoverbear] with
  [my modifications to avoid `sudo`][nosudo] (in particular, it
  requires [an encypted `GH_TOKEN`][ghtoken])
- record total test coverage across in-crate and external tests, and
  upload to [coveralls.io][coveralls]. NB. this requires `sudo` on
  Travis, and the `test` [profile][profile] must have `debug = true`
  (this is the default)

[hoverbear]: http://www.hoverbear.org/2015/03/07/rust-travis-github-pages/
[nosudo]: http://huonw.github.io/blog/2015/04/little-libraries/#the-process
[ghtoken]: http://www.hoverbear.org/2015/03/07/rust-travis-github-pages/#givingtravispermissions
[coveralls]: http://coveralls.io
[profile]: http://doc.crates.io/manifest.html#the-[profile.*]-sections

The script is designed to automatically work with both Python 2 and
Python 3.

## Installation

```
pip install 'travis-cargo<0.2' --user
export PATH=$HOME/.local/bin:$PATH
```

NB. `travis-cargo` follows semantic versioning rules, so breaking
changes may occur between `0.x` and `0.(x+1)`, and between major
versions. One should use the version-restriction syntax demonstrated
above to protect against this.

## Help

```
usage: travis-cargo [-h] [-q] [--only VERSION]
                    {coveralls,doc-upload,COMMAND} [ARGS [ARGS ...]]

manages interactions between travis and cargo/rust compilers

positional arguments:
  {coveralls,doc-upload,COMMAND}
                        the command to run, unrecognised COMMANDs are passed
                        to cargo
  ARGS                  additional arguments

optional arguments:
  -h, --help            show this help message and exit
  -q, --quiet           don't pass --verbose to cargo
  --only VERSION        only run the given command if the specified version
                        matches `TRAVIS_RUST_VERSION`
```

### `coveralls`

```
usage: travis-cargo coveralls [-h] [ARGS [ARGS ...]]

record coverage of `cargo test` and upload to coveralls.io with kcov, this
runs all binaries that `cargo test` runs but not doc tests

positional arguments:
  ARGS        arguments to pass to `cargo test`

optional arguments:
  -h, --help  show this help message and exit
```

### `doc-upload`

```
usage: travis-cargo doc-upload [-h]

use ghp-import to upload cargo-rendered docs from the master branch

optional arguments:
  -h, --help  show this help message and exit
```

## Example

A possible `.travis.yml` configuration is:

```yaml
language: rust
# necessary for `travis-cargo coveralls`
sudo: required
# run builds for both the nightly and beta branch
rust:
  - nightly
  - beta

# load travis-cargo
before_script:
  - |
      pip install 'travis-cargo<0.2' --user &&
      export PATH=$HOME/.local/bin:$PATH

# the main build
script:
  - |
      travis-cargo build &&
      travis-cargo test &&
      travis-cargo bench &&
      travis-cargo --only beta doc
after_success:
  # upload the documentation from the build with beta (automatically only actually
  # runs on the master branch)
  - travis-cargo --only beta doc-upload
  # measure code coverage and upload to coveralls.io
  - travis-cargo coveralls

env:
  global:
    # override the default `--features unstable` used for the nightly branch (optional)
    - TRAVIS_CARGO_NIGHTLY_FEATURE=nightly
    # encrypted github token for doc upload (see `GH_TOKEN` link above)
    - secure: "..."
```

Extra arguments can be passed to `cargo` invocations, although
`-`-prefixed arguments will need to occur after a `--`, e.g. `travis-cargo
build -- --features something`.
