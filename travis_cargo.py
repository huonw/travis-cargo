import argparse
import os, sys, subprocess, json, re

def run(*args):
    ret = subprocess.call(args,  stdout=sys.stdout, stderr=sys.stderr)
    if ret != 0:
        exit(ret)

def target_binary_name(target):
    return target['name'].replace('-', '_') + target['metadata']['extra_filename']

class Manifest(object):
    def __init__(self, dir):
        try:
            output = subprocess.check_output(['cargo', 'read-manifest', '--manifest-path', dir],
                                             stderr=sys.stderr)
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            exit(e.returncode)
        self.manifest = json.loads(output.decode())
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


def cargo(version, manifest, global_args, subcommand, args):
    cargo_args = args.cargo_args
    if subcommand == 'bench' and version != 'nightly':
        print('skipping `cargo bench` on non-nightly version')
        return

    add_features(cargo_args, version)

    if not global_args.quiet and '--verbose' not in cargo_args and '-v' not in cargo_args:
        cargo_args.append('--verbose')

    run('cargo', subcommand, *cargo_args)

def doc_upload(version, manifest, global_args, subcommand, args):
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

def coveralls(version, manifest, global_args, subcommand, args):
    job_id = os.environ['TRAVIS_JOB_ID']

    cargo_args = args.cargo_args
    add_features(cargo_args, version)

    test_binaries = []

    # look through the output of `cargo test` to find the test
    # binaries.
    # FIXME: the information cargo feeds us is
    # inconsistent/inaccurate, so using the output of read-manifest is
    # far too much trouble.
    try:
        output = subprocess.check_output(['cargo', 'test'] + list(cargo_args),
                                         stderr=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(e.output.decode())
        exit(e.returncode)
    output = output.decode()
    running = re.compile('^     Running target/debug/(.*)$', re.M)
    for line in running.finditer(output):
        test_binaries.append(line.group(1))

    # build kcov:
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

    # record coverage for each binary
    for binary in test_binaries:
        print('Recording %s' % binary)
        run('kcov', '--exclude-pattern=/.cargo', 'target/kcov-' + binary,
            'target/debug/' + binary)
    # merge all the coverages and upload in one go
    print('Uploading coverage')
    run('kcov', '--merge', '--coveralls-id=' + job_id, 'target/kcov',
        *('target/kcov-' + b for b in test_binaries))


# user interface

class ScInfo(object):
    def __init__(self, func, description, arguments):
        self.func = func
        self.description = description
        self.arguments = arguments
        for _name, options in arguments:
            assert isinstance(options, dict)

SC_INFO = {
    'doc-upload': ScInfo(func = doc_upload,
                         description = 'use ghp-import to upload cargo-rendered '
                         'docs from the master branch',
                         arguments = []),
    'coveralls': ScInfo(func = coveralls,
                        description = 'record coverage of `cargo test` and upload to '
                        'coveralls.io with kcov, this runs all binaries that `cargo test` runs '
                        'but not doc tests',
                    arguments = [(['cargo_args'], {
                        'metavar': 'ARGS',
                        'nargs': '*',
                        'help': 'arguments to pass to `cargo test`'
                    })]),
}
DEFAULT_SC_INFO = ScInfo(
    func = cargo,
    description = 'runs `cargo {name}`',
    arguments = [(['cargo_args'], {
        'metavar': 'ARGS',
        'nargs': '*',
        'help': 'arguments to pass to `cargo test`'
    })])

def main():
    # main parser
    parser = argparse.ArgumentParser(description = 'manages interactions between travis '
                                     'and cargo/rust compilers')

    parser.add_argument('-q','--quiet', action='store_true', default=False,
                        help='don\'t pass --verbose to cargo')
    parser.add_argument('--only', metavar='VERSION',
                        help='only run the given command if the specified version matches '
                        '`TRAVIS_RUST_VERSION`')
    parser.add_argument('command', metavar='{coveralls,doc-upload,COMMAND}',
                        help='the command to run, unrecognised COMMANDs are passed to cargo')
    parser.add_argument('args', metavar='ARGS', nargs='*',
                        help='additional arguments')

    global_args = parser.parse_args()

    # parser for the individual subcommand
    info = SC_INFO.get(global_args.command, DEFAULT_SC_INFO)
    descr = info.description.format(name = global_args.command)
    subcommand_parser = argparse.ArgumentParser(prog=sys.argv[0] + ' ' + global_args.command,
                                                description = descr)
    for name, options in info.arguments:
        subcommand_parser.add_argument(*name, **options)
    args = subcommand_parser.parse_args(global_args.args)


    version = os.environ['TRAVIS_RUST_VERSION']
    if global_args.only and global_args.only != version:
        return

    manifest = Manifest(os.getcwd())
    info.func(version, manifest, global_args, global_args.command, args)
