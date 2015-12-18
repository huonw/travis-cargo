from __future__ import print_function
import argparse
import os, sys, subprocess, json, re

def run(*args):
    ret = subprocess.call(args,  stdout=sys.stdout, stderr=sys.stderr)
    if ret != 0:
        exit(ret)

def run_filter(filter, *args):
    replacement = 'X' * len(filter)
    try:
        output = subprocess.check_output(args,
                                         stderr = subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print(e.output.decode('utf-8').replace(filter, replacement))
        exit(e.returncode)
    print(output.decode('utf-8').replace(filter, replacement))

def run_output(*args):
    try:
        output = subprocess.check_output(args,
                                         stderr=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(e.output.decode('utf-8'))
        exit(e.returncode)
    return output.decode('utf-8')

def target_binary_name(target):
    return target['name'].replace('-', '_') + target['metadata']['extra_filename']

class Manifest(object):
    def __init__(self, dir, version):
        # the --manifest-path behaviour changed in
        # https://github.com/rust-lang/cargo/pull/1955, so we need to
        # be careful to handle both
        path_file = os.path.join(dir, 'Cargo.toml')
        path_dir = dir

        try:
            output = subprocess.check_output(['cargo', 'read-manifest', '--manifest-path',
                                              path_file],
                                             stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            try:
                output = subprocess.check_output(['cargo', 'read-manifest', '--manifest-path',
                                                  path_dir],
                                                 stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e2:
                print('Cargo failed to read `--manifest-path {}`'
                      ' and `--manifest-path {}`:' % (path_file, path_dir),
                      file = sys.sdterr)
                print(e.output.decode('utf-8'))
                print(e2.output.decode('utf-8'))
                exit(e.returncode)

        self.manifest = json.loads(output.decode('utf-8'))

    def targets(self):
        return self.manifest['targets']
    def lib_name(self):
        for target in self.targets():
            if 'lib' in target['kind']:
                return target['name'].replace('-', '_')
        return None


def add_features(cargo_args, version):
    nightly_feature = os.environ.get('TRAVIS_CARGO_NIGHTLY_FEATURE', 'unstable')
    if version == 'nightly' and nightly_feature != '':
        # only touch feature arguments when we are actually going to
        # add something non-trivial, avoids problems like that in
        # issue #14 (can't use -p ... on nightly even with an empty
        # nightly feature).
        for i in range(0, len(cargo_args)):
            if cargo_args[i] == '--features':
                cargo_args[i + 1] += ' ' + nightly_feature
                break
            elif cargo_args[i].startswith('--features='):
                cargo_args[i] += ' ' + nightly_feature
                break
        else:
            cargo_args += ['--features', nightly_feature]


def cargo_raw(feature, version, manifest, args):
    cargo_args = args.cargo_args
    subcommand = args.subcommand
    if subcommand == 'bench' and version != 'nightly':
        print('skipping `cargo bench` on non-nightly version')
        return

    if feature:
        add_features(cargo_args, version)

    if not args.quiet and '--verbose' not in args and '-v' not in cargo_args:
        cargo_args.append('--verbose')

    run('cargo', subcommand, *cargo_args)

def cargo_feature(version, manifest, args):
    cargo_raw(True, version, manifest, args)
def cargo_no_feature(version, manifest, args):
    cargo_raw(False, version, manifest, args)

def doc_upload(version, manifest, args):
    branch = os.environ.get('APPVEYOR_REPO_BRANCH') or os.environ['TRAVIS_BRANCH']
    repo = os.environ.get('APPVEYOR_REPO_NAME') or os.environ['TRAVIS_REPO_SLUG']
    if os.environ.get('APPVEYOR_PULL_REQUEST_NUMBER'):
        pr = 'true'
    else:
        pr = os.environ.get('TRAVIS_PULL_REQUEST', 'false')

    lib_name = manifest.lib_name()
    if lib_name is None:
        sys.stderr.write('error: uploading docs for package with no library')
        exit(1)

    if branch == args.branch and pr == 'false':
        # only load the token when we're sure we're uploading (travis
        # won't decrypt secret keys for PRs, so loading this with the
        # other vars causes problems with tests)
        token = os.environ['GH_TOKEN']

        print('uploading docs...')
        sys.stdout.flush()
        with open('target/doc/index.html', 'w') as f:
            f.write('<meta http-equiv=refresh content=0;url=%s/index.html>' % lib_name)

        run('git', 'clone', 'https://github.com/davisp/ghp-import')
        run(sys.executable, './ghp-import/ghp-import', '-n', 'target/doc')
        run_filter(token, 'git', 'push', '-fq', 'https://%s@github.com/%s.git' % (token, repo), 'gh-pages')

def build_kcov(use_sudo, verify):
    deps = ''
    if use_sudo:
        deps = 'sudo apt-get install libcurl4-openssl-dev libelf-dev libdw-dev cmake'
        if verify:
            deps += ' binutils-dev'
    init = deps + '''
    wget https://github.com/SimonKagstrom/kcov/archive/master.zip
    unzip master.zip
    mv kcov-master kcov
    mkdir kcov/build
    '''
    for line in init.split('\n'):
        line = line.strip()
        if line:
            print('Running: %s' % line)
            run(*line.split())
    current = os.getcwd()
    os.chdir('kcov/build')
    build = '''
    cmake ..
    make
    '''
    for line in build.split('\n'):
        line = line.strip()
        if line:
            print('Running: %s' % line)
            run(*line.split())
    os.chdir(current)
    return os.path.join(current, 'kcov/build/src/kcov')

def raw_coverage(use_sudo, verify, test_args, merge_msg, kcov_merge_args, kcov_merge_dir):
    kcov = build_kcov(use_sudo, verify)

    test_binaries = []
    # look through the output of `cargo test` to find the test
    # binaries.
    # FIXME: the information cargo feeds us is
    # inconsistent/inaccurate, so using the output of read-manifest is
    # far too much trouble.

    output = run_output('cargo', 'test', *test_args)
    running = re.compile('^     Running target/debug/(.*)$', re.M)
    for line in running.finditer(output):
        test_binaries.append(line.group(1))


    # record coverage for each binary
    for binary in test_binaries:
        print('Recording %s' % binary)
        kcov_args = [kcov]
        if verify:
            kcov_args += ['--verify']
        kcov_args += ['--exclude-pattern=/.cargo', 'target/kcov-' + binary,
                      'target/debug/' + binary]
        run(*kcov_args)
    # merge all the coverages and upload in one go
    print(merge_msg)
    kcov_args = [kcov, '--merge'] + kcov_merge_args + [kcov_merge_dir]
    kcov_args += ('target/kcov-' + b for b in test_binaries)
    run(*kcov_args)

def coverage(version, manifest, args):
    cargo_args = args.cargo_args
    add_features(cargo_args, version)

    kcov_merge_dir = args.merge_into
    raw_coverage(not args.no_sudo, args.verify, cargo_args, 'Merging coverage', [], kcov_merge_dir)

def coveralls(version, manifest, args):
    job_id = os.environ['TRAVIS_JOB_ID']

    cargo_args = args.cargo_args
    add_features(cargo_args, version)

    raw_coverage(not args.no_sudo, args.verify, cargo_args, 'Uploading coverage',
                 ['--coveralls-id=' + job_id], 'target/kcov')


# user interface
class ScInfo(object):
    def __init__(self, func, description, arguments, help_=None, is_cargo=False):
        self.func = func
        self.help = help_
        self.description = description
        self.arguments = arguments
        self.is_cargo = is_cargo
        for _name, options in arguments:
            assert isinstance(options, dict)

NO_SUDO = (['--no-sudo'], {
    'action': 'store_true',
    'default': False,
    'help': 'don\'t use `sudo` to install kcov\'s deps. Requires that '
    'libcurl4-openssl-dev, libelf-dev and libdw-dev are installed (e.g. via '
    '`addons: apt: packages:`)'
})
VERIFY = (['--verify'], {
    'action': 'store_true',
    'default': False,
    'help': 'pass `--verify` to kcov, to avoid some crashes. See '
    '<https://github.com/huonw/travis-cargo/issues/12>. This requires '
    'installing the `binutils-dev` package.'
})

SC_INFO = {
    'doc-upload': ScInfo(func = doc_upload,
                         description = 'Use ghp-import to upload cargo-rendered '
                         'docs to Github Pages, from the master branch.',
                         help_ = 'upload documentation to Github pages.',
                         arguments = [(['--branch'], {
                             'default': 'master',
                             'help': 'upload docs when on this branch, defaults to master',
                         })]),
    'coveralls': ScInfo(func = coveralls,
                        description = 'Record coverage of `cargo test` and upload to '
                        'coveralls.io with kcov, this runs all binaries that `cargo test` runs '
                        'but not doc tests. Merged kcov results can be accessed in `target/kcov`.',
                        help_ = 'record and upload code coverage to coveralls.io',
                        arguments = [(['cargo_args'], {
                            'metavar': 'ARGS',
                            'nargs': '*',
                            'help': 'arguments to pass to `cargo test`'
                        }),
                                     NO_SUDO,
                                     VERIFY]),
    'coverage': ScInfo(func = coverage,
                       description = 'Record coverage of `cargo test`, this runs all '
                       'binaries that `cargo test` runs but not doc tests. The results '
                       'of all tests are merged into a single directory.',
                       help_ = 'record code coverage',
                       arguments = [(['cargo_args'], {
                           'metavar': 'ARGS',
                           'nargs': '*',
                           'help': 'arguments to pass to `cargo test`'
                       }),
                                    (['-m', '--merge-into'], {
                                        'metavar': 'DIR',
                                        'default': 'target/kcov',
                                        'help': 'the directory to put the final merged kcov '
                                        'result into (default `target/kcov`)'
                                    }),
                                    NO_SUDO,
                                    VERIFY])
}

def cargo_sc(name, features):
    return ScInfo(func = cargo_feature if features else cargo_no_feature,
                  description = 'Run `cargo %s`' % name,
                  is_cargo = True,
                  arguments = [(['cargo_args'], {
                      'metavar': 'ARGS',
                      'nargs': '*',
                      'help': 'arguments to pass to `cargo %s`' % name
                  })])

NO_FEATURE_CARGO = [
    'clean', 'fetch', 'generate-lockfile', 'git-checkout', 'help', 'locate-project',
    'login', 'new', 'owner', 'package', 'pkgid', 'publish', 'read-manifest', 'search',
    'update', 'verify-project', 'version', 'yank'
]
FEATURE_CARGO = [
    'build', 'bench', 'test', 'doc', 'run', 'rustc', 'rustdoc',
]
SC_INFO.update((c, cargo_sc(c, False)) for c in NO_FEATURE_CARGO)
SC_INFO.update((c, cargo_sc(c, True)) for c in FEATURE_CARGO)

def main():
    parser = argparse.ArgumentParser(description = '''
Manages interactions between Travis and Cargo and common tooling tasks.
''')

    parser.add_argument('-q','--quiet', action='store_true', default=False,
                        help='don\'t pass --verbose to cargo subcommands')
    parser.add_argument('--only', metavar='VERSION',
                        help='only run the given command if the specified version matches '
                        '`TRAVIS_RUST_VERSION`')
    parser.add_argument('--skip', metavar='VERSION',
                        help='only run the given command if the specified version does not match '
                        '`TRAVIS_RUST_VERSION`')

    sb = parser.add_subparsers(metavar = '{coverage,coveralls,doc-upload,...}',
                               description = '''

travis-cargo supports all cargo subcommands, and selected others
(listed below).

Cargo subcommands have `--verbose` added to their invocation by
default, and, when running with a nightly compiler, `--features
unstable` (or `--features $TRAVIS_CARGO_NIGHTLY_FEATURE` if that
environment variable is defined) if `--features` is a valid argument.

''',
                               dest = 'subcommand')
    for _, name, sc in sorted((sc.is_cargo, n, sc) for n, sc in SC_INFO.items()):
        extra_args = {'help': sc.help} if sc.help is not None else {}
        sub_parser = sb.add_parser(name,
                                   description = sc.description,
                                   **extra_args)
        sub_parser.set_defaults(func = sc.func)
        for name, options in sc.arguments:
            sub_parser.add_argument(*name, **options)

    args = parser.parse_args()

    version = os.environ.get('TRAVIS_RUST_VERSION', None)
    if version is None:
        # fill in the version based on the compiler's version output.
        output = run_output('rustc', '-V')
        phrases = ['nightly', ('dev', 'nightly'), 'beta']
        for phrase in phrases:
            if isinstance(phrase, tuple):
                alias = phrase[1]
                phrase = phrase[0]
            else:
                alias = phrase
            if phrase in output:
                version = alias
                break

    if args.only and args.only != version:
        return

    if args.skip and args.skip == version:
      return

    manifest = Manifest(os.getcwd(), version)
    args.func(version, manifest, args)
