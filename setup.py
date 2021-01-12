from setuptools import find_packages, setup

name = "laminar"
description = "Run workflows that you love."
with open("README.md", "r") as readme:
    long_description = readme.read()


setup(
    author="Ryan Chui",
    author_email="ryan.w.chui@gmail.com",
    description=description,
    license="GPLv3",
    long_description=long_description,
    name=name,
    package_data={name: ["_/*/*"]},
    packages=find_packages(),
    include_package_data=True,
    url="https://github.com/rchui/" + name,
    version="0.0.0",
    install_requires=[],
    setup_requires=[],
)
