#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open("README.md") as readme_file:
    readme = readme_file.read()

with open("CHANGELOG.md") as history_file:
    history = history_file.read()

requirements = []

setup_requirements = []

test_requirements = []


setup(
    author="Nabil-Fareed Alikhan",
    author_email="nabil@happykhan.com",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    description="This is a fork of phac-nml/irida-uploader . I have added some extra parsers that cater"
                " to my specific needs.",
    install_requires=requirements,
    license="License :: OSI Approved :: Apache Software License",
    long_description=readme + "\n\n" + history,
    long_description_content_type="text/markdown",
    include_package_data=True,
    keywords="qi-irida-uploader",
    name="QI IRIDA Uploader",
    packages=find_packages(include=["qi-irida-uploader"]),
    scripts=['upload_run.py'],
    setup_requires=setup_requirements,
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/happykhan/qi-irida-uploader",
    version="1.0.3",
    zip_safe=False,
)
