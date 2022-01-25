#!/usr/bin/env python
from setuptools import setup

from outputs import VERSION

setup(
    name='django-outputs',
    version=VERSION,
    description='Exports and schedulers for Django',
    long_description=open('README.md').read(),
    author='Pragmatic Mates',
    author_email='info@pragmaticmates.com',
    maintainer='Pragmatic Mates',
    maintainer_email='info@pragmaticmates.com',
    url='https://github.com/PragmaticMates/django-outputs',
    packages=[
        'outputs',
        'outputs.migrations'
    ],
    include_package_data=True,
    install_requires=('django', 'django-rq', 'django-crispy-forms', 'django-whistle', 'django-pragmatic'),
    classifiers=[
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Operating System :: OS Independent',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Framework :: Django',
        'License :: OSI Approved :: BSD License',
        'Development Status :: 3 - Alpha'
    ],
    license='GPLv3',
    keywords="django outputs export scheduler rq redis",
)
