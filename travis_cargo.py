import argparse
import os, sys, subprocess, json, re

def run(*args):
    ret = subprocess.call(args,  stdout=sys.stdout, stderr=sys.stderr)
    if ret != 0:
        exit(ret)
def run_output(*args):
    try:
        output = subprocess.check_output(args,
                                         stderr=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(e.output.decode())
        exit(e.returncode)
    return output.decode()

def target_binary_name(target):
    return target['name'].replace('-', '_') + target['metadata']['extra_filename']

class Manifest(object):
    def __init__(self, dir):
        self.manifest = json.loads(run_output('cargo', 'read-manifest', '--manifest-path', dir))
    def targets(self):
        return self.manifest['targets']
    def lib_name(self):
        for target in self.targets():
            if 'lib' in target['kind']:
                return target['name'].replace('-', '_')
        return None


def add_features(cargo_args, version):
    nightly_feature = os.environ.get('TRAVIS_CARGO_NIGHTLY_FEATURE', 'unstable')
    if version == 'nightly':
        for i in range(0, len(cargo_args)):
            if cargo_args[i] == '--features':
                cargo_args[i + 1] += ' ' + nightly_feature
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
    branch = os.environ['TRAVIS_BRANCH']
    pr = os.environ['TRAVIS_PULL_REQUEST']
    token = os.environ['GH_TOKEN']
    repo = os.environ['TRAVIS_REPO_SLUG']

    lib_name = manifest.lib_name()
    if lib_name is None:
        sys.stderr.write('error: uploading docs for package with no library')
        exit(1)

    if branch == 'master' and pr == 'false':
        print('uploading docs...')
        sys.stdout.flush()
        with open('target/doc/index.html', 'w') as f:
            f.write('<meta http-equiv=refresh content=0;url=%s/index.html>' % lib_name)

        run('git', 'clone', 'https://github.com/davisp/ghp-import')
        run('./ghp-import/ghp-import', '-n', 'target/doc')
        run('git', 'push', '-fq', 'https://%s@github.com/%s.git' % (token, repo), 'gh-pages')

def build_kcov():
    init = '''
    sudo apt-get install libcurl4-openssl-dev libelf-dev libdw-dev cmake
    git clone --depth 1 https://github.com/SimonKagstrom/kcov
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
    sudo make install
    '''
    for line in build.split('\n'):
        line = line.strip()
        if line:
            print('Running: %s' % line)
            run(*line.split())
    os.chdir(current)

def raw_coverage(test_args, merge_msg, kcov_merge_args, kcov_merge_dir):
    build_kcov()

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
        run('kcov', '--exclude-pattern=/.cargo', 'target/kcov-' + binary,
            'target/debug/' + binary)
    # merge all the coverages and upload in one go
    print(merge_msg)
    kcov_args = ['kcov', '--merge'] + kcov_merge_args + [kcov_merge_dir]
    kcov_args += ('target/kcov-' + b for b in test_binaries)
    run(*kcov_args)

def coverage(version, manifest, args):
    cargo_args = args.cargo_args
    add_features(cargo_args, version)

    kcov_merge_dir = args.merge_into
    raw_coverage(cargo_args, 'Merging coverage', [], kcov_merge_dir)

def coveralls(version, manifest, args):
    job_id = os.environ['TRAVIS_JOB_ID']

    cargo_args = args.cargo_args
    add_features(cargo_args, version)

    raw_coverage(cargo_args, 'Uploading coverage',
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

SC_INFO = {
    'doc-upload': ScInfo(func = doc_upload,
                         description = 'Use ghp-import to upload cargo-rendered '
                         'docs to Github Pages, from the master branch.',
                         help_ = 'upload documentation to Github pages.',
                         arguments = []),
    'coveralls': ScInfo(func = coveralls,
                        description = 'Record coverage of `cargo test` and upload to '
                        'coveralls.io with kcov, this runs all binaries that `cargo test` runs '
                        'but not doc tests. Merged kcov results can be accessed in `target/kcov`.',
                        help_ = 'record and upload code coverage to coveralls.io',
                        arguments = [(['cargo_args'], {
                            'metavar': 'ARGS',
                            'nargs': '*',
                            'help': 'arguments to pass to `cargo test`'
                        })]),
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
                                    })])
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
    'build', 'bench', 'test', 'doc', 'run'
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

    manifest = Manifest(os.getcwd())
    args.func(version, manifest, args)
