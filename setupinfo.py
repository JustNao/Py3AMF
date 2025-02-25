# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Meta data and helper functions for setup
"""

import fnmatch
import os.path
import platform
import sys

try:
    from Cython.Distutils import build_ext

    have_cython = True
except ImportError:
    from setuptools.command.build_ext import build_ext

    have_cython = False


from setuptools.command import test, sdist
from setuptools import Extension
from distutils.core import Distribution


_version = None

can_compile_extensions = platform.python_implementation() == "CPython"


class MyDistribution(Distribution):
    """
    This seems to be is the only obvious way to add a global option to
    distutils.

    Provide the ability to disable building the extensions for any called
    command.
    """

    global_options = Distribution.global_options + [
        ('disable-ext', None, 'Disable building extensions.')
    ]

    def finalize_options(self):
        Distribution.finalize_options(self)

        try:
            i = self.script_args.index('--disable-ext')
        except ValueError:
            self.disable_ext = False
        else:
            self.disable_ext = True
            self.script_args.pop(i)


class MyBuildExt(build_ext):
    """
    The companion to L{MyDistribution} that checks to see if building the
    extensions are disabled.
    """

    def run(self, *args, **kwargs):
        if self.distribution.disable_ext:
            return

        build_ext.run(self, *args, **kwargs)


class MySDist(sdist.sdist):
    """
    We generate the Cython code for a source distribution
    """

    def cythonise(self):
        ext = MyBuildExt(self.distribution)
        ext.initialize_options()
        ext.finalize_options()

        ext.check_extensions_list(ext.extensions)

        for e in ext.extensions:
            e.sources = ext.cython_sources(e.sources, e)

    def run(self):
        if not have_cython:
            print('ERROR - Cython is required to build source distributions')

            raise SystemExit(1)

        self.cythonise()

        return sdist.sdist.run(self)


class TestCommand(test.test):
    """
    Ensures that unittest2 is imported if required and replaces the old
    unittest module.
    """

    def run_tests(self):
        try:
            import unittest2

            sys.modules['unittest'] = unittest2
        except ImportError:
            pass

        return test.test.run_tests(self)


def set_version(version):
    global _version

    _version = version


def get_version():
    v = ''
    prev = None

    for x in _version:
        if prev is not None:
            if isinstance(x, int):
                v += '.'

        prev = x
        v += str(x)

    return v.strip('.')


def get_extras_require():
    return {
        'twisted': ['Twisted>=16.0.0'],
        'django': ['Django>=0.96'],
        'sqlalchemy': ['SQLAlchemy>=0.4'],
        'elixir': ['Elixir>=0.7.1'],
        'lxml': ['lxml>=4.4.0'],
        'six': ['six>=1.10.0']
    }


def get_package_data():
    return {
        'cpyamf': ['*.pxd'],
    }


def extra_setup_args():
    """
    Extra kwargs to supply in the call to C{setup}.

    This is used to supply custom commands, not metadata - that should live in
    setup.py itself.
    """
    return {
        'distclass': MyDistribution,
        'cmdclass': {
            'test': TestCommand,
            'build_ext': MyBuildExt,
            'sdist': MySDist
        },
        'package_data': get_package_data(),
    }


def get_install_requirements():
    """
    Returns a list of dependencies for PyAMF to function correctly on the
    target platform.
    """
    install_requires = ['defusedxml']

    if 'dev' in get_version():
        if can_compile_extensions:
            install_requires.extend(['Cython>=0.28'])

    return install_requires


def get_test_requirements():
    """
    Returns a list of required packages to run the test suite.
    """
    tests_require = []

    return tests_require


def write_version_py(filename='pyamf/_version.py'):
    """
    """
    if os.path.exists(filename):
        os.remove(filename)

    content = """\
# THIS FILE IS GENERATED BY PYAMF SETUP.PY
from pyamf.versions import Version

version = Version(*%(version)r)
"""
    a = open(filename, 'wt')

    try:
        a.write(content % {'version': _version})
    finally:
        a.close()


def make_extension(mod_name, **extra_options):
    """
    Tries is best to return an Extension instance based on the mod_name
    """
    base_name = os.path.join(mod_name.replace('.', os.path.sep))

    if have_cython:
        for ext in ['.pyx', '.py']:
            source = base_name + ext

            if os.path.exists(source):
                return Extension(mod_name, [source], **extra_options)

        print('WARNING: Could not find Cython source for %r' % (mod_name,))
    else:
        source = base_name + '.c'

        if os.path.exists(source):
            return Extension(mod_name, [source], **extra_options)

        print('WARNING: Could not build extension for %r, no source found' % (
            mod_name,))


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def get_extensions():
    """
    Return a list of Extension instances that can be compiled.
    """
    if not can_compile_extensions:
        # due to changes in pip these prints have no effect
        print(80 * '*')
        print('WARNING:')
        print(
            '\tAn optional code optimization (C extension) could not be '
            'compiled.\n\n'
        )
        print('\tOptimizations for this package will not be available!\n\n')
        print('Compiling extensions is not supported on %r' % (sys.platform,))
        print(80 * '*')

        return []

    extensions = []

    for p in recursive_glob('.', '*.pyx'):
        mod_name = os.path.splitext(p)[0].replace(os.path.sep, '.')

        e = make_extension(mod_name)

        if e:
            extensions.append(e)

    return extensions


def get_trove_classifiers():
    """
    Return a list of trove classifiers that are setup dependent.
    """
    classifiers = []

    def dev_status():
        version = get_version()

        if 'dev' in version:
            return 'Development Status :: 2 - Pre-Alpha'
        elif 'alpha' in version:
            return 'Development Status :: 3 - Alpha'
        elif 'beta' in version:
            return 'Development Status :: 4 - Beta'
        else:
            return 'Development Status :: 5 - Production/Stable'

    return classifiers + [dev_status()]


def recursive_glob(path, pattern):
    matches = []

    for root, dirnames, filenames in os.walk(path):
        for filename in fnmatch.filter(filenames, pattern):
            matches.append(os.path.normpath(os.path.join(root, filename)))

    return matches
