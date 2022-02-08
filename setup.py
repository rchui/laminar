import ast
import re
from typing import Any, cast

from setuptools import find_packages, setup

with open("README.md", "r") as readme, open("requirements.txt", "r") as requirements, open(
    "laminar/__init__.py", "rb"
) as init:
    setup(
        author="Ryan Chui",
        author_email="ryan.w.chui@gmail.com",
        classifiers=[
            "Development Status :: 3 - Alpha",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
            "Programming Language :: Python :: 3",
            "Topic :: Software Development :: Libraries :: Application Frameworks",
            "Typing :: Typed",
        ],
        description="Modern, container first framework for creating ready for production workflows.",
        include_package_data=True,
        install_requires=requirements.read(),
        license="MIT",
        long_description=readme.read(),
        name="laminar",
        packages=find_packages(exclude=["tests"]),
        url="https://github.com/rchui/laminar",
        version=str(
            ast.literal_eval(cast(Any, re.search(r"__version__\s+=\s+(.*)", init.read().decode("utf-8"))).group(1))
        ),
    )
