# -*- coding: utf-8 -*-
import os
from setuptools import setup


with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

with open('requirements.txt') as requirements:
    required = requirements.read().splitlines()


def get_packages(package):
    """
    Return root package and all sub-packages.
    """
    return [
        dirpath for dirpath, dirnames, filenames in os.walk(package)
        if os.path.exists(os.path.join(dirpath, '__init__.py'))]


# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='drf-complete-metadata',
    version='1.0.0',
    packages=get_packages('complete_metadata'),
    include_package_data=True,
    description='This package provides custom metadata class for Django Rest Framework to enrich data returned by OPTIONS requests in easy way.',
    long_description=README,
    long_description_content_type='text/markdown',
    author='IIIT',
    author_email='github@iiit.pl',
    install_requires=required,
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)
