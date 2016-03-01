# travis-cargo

[![Build Status](https://travis-ci.org/huonw/travis-cargo.svg?branch=master)](https://travis-ci.org/huonw/travis-cargo)

This provides a standalone script `travis-cargo` that manages running
cargo and several other related features on [Travis CI][travis] (and
somewhat on [AppVeyor]).

[travis]: http://travis-ci.org
[AppVeyor]: http://www.appveyor.com/

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
- [travis-cargo 0.1.3: --no-sudo][nosudo]

[train]: http://huonw.github.io/blog/2015/04/helping-travis-catch-the-rustc-train/
[part2]: http://huonw.github.io/blog/2015/05/travis-on-the-train-part-2/
[nosudo]: http://huonw.github.io/blog/2015/06/travis-cargo-0.1.3/

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
sudo: false
language: rust
# necessary for `travis-cargo coveralls --no-sudo`
addons:
  apt:
    packages:
      - libcurl4-openssl-dev
      - libelf-dev
      - libdw-dev
      - binutils-dev # optional: only required for the --verify flag of coveralls

# run builds for all the trains (and more)
rust:
  - nightly
  - beta
  # check it compiles on the latest stable compiler
  - stable
  # and the first stable one (this should be bumped as the minimum
  # Rust version required changes)
  - 1.0.0

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
      travis-cargo --only stable doc
after_success:
  # upload the documentation from the build with stable (automatically only actually
  # runs on the master branch, not individual PRs)
  - travis-cargo --only stable doc-upload
  # measure code coverage and upload to coveralls.io (the verify
  # argument mitigates kcov crashes due to malformed debuginfo, at the
  # cost of some speed <https://github.com/huonw/travis-cargo/issues/12>)
  - travis-cargo coveralls --no-sudo --verify

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
`TRAVIS_CARGO_NIGHTLY_FEATURE=""` should avoid errors caused by undefined
features.


## Help

```
usage: travis-cargo [-h] [-q] [--only VERSION] [--skip VERSION]
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
usage: travis-cargo coverage [-h] [-m DIR] [--exclude-pattern PATTERN]
                             [--kcov-options OPTION] [--no-sudo] [--verify]
                             [ARGS [ARGS ...]]

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
  --exclude-pattern PATTERN
                        pass additional comma-separated exclusionary patterns
                        to kcov. See <https://github.com/SimonKagstrom/kcov
                        #filtering-output> for how patterns work. By default,
                        the /.cargo pattern is ignored. Example: --exclude-
                        pattern="test/,bench/"
  --kcov-options OPTION
                        pass additional arguments to kcov, apart from --verify
                        and --exclude-pattern, when recording coverage.
                        Specify multiple times for multiple arguments.
                        Example: --kcov-options="--debug=31"
  --no-sudo             don't use `sudo` to install kcov's deps. Requires that
                        libcurl4-openssl-dev, libelf-dev and libdw-dev are
                        installed (e.g. via `addons: apt: packages:`)
  --verify              pass `--verify` to kcov, to avoid some crashes. See
                        <https://github.com/huonw/travis-cargo/issues/12>.
                        This requires installing the `binutils-dev` package.
```

### `coveralls`

```
usage: travis-cargo coveralls [-h] [--exclude-pattern PATTERN]
                              [--kcov-options OPTION] [--no-sudo] [--verify]
                              [ARGS [ARGS ...]]

Record coverage of `cargo test` and upload to coveralls.io with kcov, this
runs all binaries that `cargo test` runs but not doc tests. Merged kcov
results can be accessed in `target/kcov`.

positional arguments:
  ARGS                  arguments to pass to `cargo test`

optional arguments:
  -h, --help            show this help message and exit
  --exclude-pattern PATTERN
                        pass additional comma-separated exclusionary patterns
                        to kcov. See <https://github.com/SimonKagstrom/kcov
                        #filtering-output> for how patterns work. By default,
                        the /.cargo pattern is ignored. Example: --exclude-
                        pattern="test/,bench/"
  --kcov-options OPTION
                        pass additional arguments to kcov, apart from --verify
                        and --exclude-pattern, when recording coverage.
                        Specify multiple times for multiple arguments.
                        Example: --kcov-options="--debug=31"
  --no-sudo             don't use `sudo` to install kcov's deps. Requires that
                        libcurl4-openssl-dev, libelf-dev and libdw-dev are
                        installed (e.g. via `addons: apt: packages:`)
  --verify              pass `--verify` to kcov, to avoid some crashes. See
                        <https://github.com/huonw/travis-cargo/issues/12>.
                        This requires installing the `binutils-dev` package.
```

### `doc-upload`

```
usage: travis_cargo.py doc-upload [-h] [--branch BRANCH]

Use ghp-import to upload cargo-rendered docs to Github Pages, from the master
branch.

optional arguments:
  -h, --help       show this help message and exit
  --branch BRANCH  upload docs when on this branch, defaults to master
```
