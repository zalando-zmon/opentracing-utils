#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Setup file for opentracing-utils.
"""
from setuptools import setup, find_packages


TEST_REQUIREMENTS = (
    'basictracer',
    'mock==2.0.0',
    'opentracing',
    'pytest',
    'pytest_cov',
    'requests',
    # Third party tracers
    'instana',
    'lightstep',
)

MAIN_PACKAGE = 'opentracing_utils'
VERSION = '0.5'
DESCRIPTION = 'OpenTracing utilities'


setup(
    name='opentracing-utils',
    version=VERSION,
    description=DESCRIPTION,
    long_description=open('README.rst').read(),
    license=open('LICENSE').read(),
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
