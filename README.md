# travis-cargo

[![Build Status](https://travis-ci.org/huonw/travis-cargo.svg?branch=master)](https://travis-ci.org/huonw/travis-cargo)

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

I've written some things about this:

- [Helping Travis catch the rustc train][train]
- [Travis on the train, part 2][part2]

[train]: http://huonw.github.io/blog/2015/04/helping-travis-catch-the-rustc-train/
[part2]: http://huonw.github.io/blog/2015/05/travis-on-the-train-part-2/

## Installation

```
pip install 'travis-cargo<0.2' --user
export PATH=$HOME/.local/bin:$PATH
```

NB. `travis-cargo` follows semantic versioning rules, so breaking
changes may occur between `0.x` and `0.(x+1)`, and between major
versions. One should use the version-restriction syntax demonstrated
above to protect against this.

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

If you do not wish to define an `unstable` or similar feature, setting
`TRAVIS_CARGO_NIGHTLY_FEATURE=` should avoid errors caused by
undefined features.

## Help

```
usage: travis-cargo [-h] [-q] [--only VERSION]
                    {coverage,coveralls,doc-upload,...} ...

Manages interactions between Travis and Cargo and common tooling tasks.

optional arguments:
  -h, --help            show this help message and exit
  -q, --quiet           don't pass --verbose to cargo subcommands
  --only VERSION        only run the given command if the specified version
                        matches `TRAVIS_RUST_VERSION`

subcommands:
  travis-cargo supports all cargo subcommands, and selected others (listed
  below). Cargo subcommands have `--verbose` added to their invocation by
  default, and, when running with a nightly compiler, `--features unstable`
  (or `--features $TRAVIS_CARGO_NIGHTLY_FEATURE` if that environment
  variable is defined) if `--features` is a valid argument.

  {coverage,coveralls,doc-upload,...}
    coverage            record code coverage
    coveralls           record and upload code coverage to coveralls.io
    doc-upload          upload documentation to Github pages.
```

### `coverage`

```
usage: travis-cargo coverage [-h] [-m DIR] [ARGS [ARGS ...]]

Record coverage of `cargo test`, this runs all binaries that `cargo test` runs
but not doc tests. The results of all tests are merged into a single
directory.

positional arguments:
  ARGS                  arguments to pass to `cargo test`

optional arguments:
  -h, --help            show this help message and exit
  -m DIR, --merge-into DIR
                        the directory to put the final merged kcov result into
                        (default `target/kcov`)
```

### `coveralls`

```
usage: travis-cargo coveralls [-h] [ARGS [ARGS ...]]

Record coverage of `cargo test` and upload to coveralls.io with kcov, this
runs all binaries that `cargo test` runs but not doc tests. Merged kcov
results can be accessed in `target/kcov`.

positional arguments:
  ARGS        arguments to pass to `cargo test`

optional arguments:
  -h, --help  show this help message and exit
```

### `doc-upload`

```
usage: travis-cargo doc-upload [-h]

Use ghp-import to upload cargo-rendered docs to Github Pages, from the master
branch.

optional arguments:
  -h, --help  show this help message and exit
```
