from setuptools import setup


setup(
    name = 'travis-cargo',
    version = '0.0.1',
    description = ('Manages interactions between travis and cargo/rust compilers.'),
    py_modules = ['travis_cargo'],
    entry_points = {
        'console_scripts': ['travis-cargo=travis_cargo:main']
    },
)
