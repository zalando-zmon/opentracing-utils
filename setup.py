#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Setup file for opentracing-utils.
"""
import io
import sys
from setuptools import setup, find_packages

PY3 = sys.version_info.major == 3

MAIN_PACKAGE = 'opentracing_utils'
VERSION = '0.15'
DESCRIPTION = 'OpenTracing utilities library'


def load_req(req):
    try:
        return [r.strip() for r in open(req).read().splitlines() if r.strip() and not r.strip().startswith('#')]
    except Exception:
        return []


TEST_REQUIREMENTS = load_req('test_requirements.txt')


if __name__ == '__main__':
    setup(
        name='opentracing-utils',
        version=VERSION,
        description=DESCRIPTION,
        long_description=io.open('README.rst', encoding='utf-8').read(),
        license='The MIT License (MIT)',
        url='https://github.com/zalando-zmon/opentracing-utils',
        packages=find_packages(exclude=['tests']),
        install_requires=[
            'future',
            'opentracing',
        ],
        setup_requires=[
            'opentracing',
            'pytest-runner',
        ],
        test_suite='tests',
        tests_require=TEST_REQUIREMENTS,
        include_package_data=True,
        classifiers=[
            'Development Status :: 4 - Beta',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python',
            'Programming Language :: Python :: Implementation :: CPython',
            'Environment :: Console',
            'Operating System :: POSIX :: Linux',
            'Operating System :: MacOS :: MacOS X',
            'Topic :: Utilities',
            'Topic :: System :: Monitoring',
            'Topic :: System :: Networking :: Monitoring',
        ]
    )
