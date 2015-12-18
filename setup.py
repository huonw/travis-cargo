from setuptools import setup, find_packages

CLASSIFIERS = [
    'License :: OSI Approved :: Apache Software License',
    'License :: OSI Approved :: MIT License',
    'Topic :: Software Development :: Testing',
    'Programming Language :: Other',
]

setup(
    name = 'travis-cargo',
    version = '0.1.12',
    description = ('Manages interactions between travis and cargo/rust compilers.'),
    author = 'Huon Wilson',
    author_email = 'dbau.pp@gmail.com',
    url = 'https://github.com/huonw/travis-cargo',
    download_url = 'https://github.com/huonw/travis-cargo/tarball/0.1.12',
    keywords = ['testing', 'travis', 'rust', 'cargo'],
    packages = find_packages(),
    py_modules = ['travis_cargo'],
    entry_points = {
        'console_scripts': ['travis-cargo=travis_cargo:main']
    },
    classifiers = CLASSIFIERS,
)
