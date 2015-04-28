#!/usr/bin/env python
import argparse
import os, sys, subprocess, json

def run(*args):
    ret = subprocess.call(args,  stdout=sys.stdout, stderr=sys.stderr)
    if ret != 0:
        exit(ret)
def find_lib_name():
    try:
        output = subprocess.check_output(['cargo', 'read-manifest', '--manifest-path', os.getcwd()],
                                         stderr=sys.stderr)
    except subprocess.CalledProcessError as e:
        exit(e.returncode)
    manifest = json.loads(output.decode())

    for target in manifest['targets']:
        if 'lib' in target['kind']:
            return target['name'].replace('-', '_')

    return None

def cargo(version, args):
    is_nightly = version == 'nightly'
    cargo_args = args.cargo_args
    nightly_feature = os.environ.get('TRAVIS_CARGO_NIGHTLY_FEATURE', 'unstable')
    if cargo_args[0] == 'bench' and not is_nightly:
        print('skipping `cargo bench` on non-nightly version')
        return

    if is_nightly:
        for i in range(0, len(cargo_args)):
            if cargo_args[i] == '--features':
                cargo_args[i + 1] += ' ' + nightly_feature
                break
        else:
            cargo_args += ['--features', nightly_feature]
    if not args.quiet and '--verbose' not in cargo_args and '-v' not in cargo_args:
        cargo_args.append('--verbose')

    run('cargo', *cargo_args)

def doc_upload(version, args):
    branch = os.environ['TRAVIS_BRANCH']
    pr = os.environ['TRAVIS_PULL_REQUEST']
    token = os.environ['GH_TOKEN']
    repo = os.environ['TRAVIS_REPO_SLUG']

    lib_name = find_lib_name()
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

def main():
    parser = argparse.ArgumentParser(description = 'manages interactions between travis '
                                     'and cargo/rust compilers')

    parser.add_argument('-q','--quiet', action='store_true', default=False,
                        help='don\'t pass --verbose to cargo')
    parser.add_argument('--only', metavar='VERSION',
                        help='only run the given command if the specified version matches '
                        '`TRAVIS_RUST_VERSION`')
    subparsers = parser.add_subparsers(title = 'subcommands')

    p_cargo = subparsers.add_parser('cargo',
                                    help = 'run cargo, passing '
                                    '`--features $TRAVIS_CARGO_NIGHTLY_FEATURE` (default '
                                    '\'unstable\') if the nightly branch is detected, and '
                                    'skipping `cargo bench` if it is not')
    p_cargo.add_argument('cargo_args', metavar='ARGS', nargs='+')
    p_cargo.set_defaults(func = cargo)

    p_doc_upload = subparsers.add_parser('doc-upload',
                                         help = 'uses ghp-import to upload cargo-rendered docs '
                                         'from the master branch')
    p_doc_upload.set_defaults(func = doc_upload)
    args = parser.parse_args()

    version = os.environ['TRAVIS_RUST_VERSION']
    if args.only and args.only != version:
        return

    args.func(version, args)

if __name__ == '__main__':
    main()
