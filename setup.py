from importlib.machinery import SourceFileLoader

from setuptools import find_packages, setup

README = "README.md"
REQUIREMENTS = "requirements.txt"
VERSION = "laminar/version.py"

with open(README, "r") as readme, open(REQUIREMENTS, "r") as requirements:
    setup(
        author="Ryan Chui",
        author_email="ryan.w.chui@gmail.com",
        classifiers=[
            "Development Status :: 3 - Alpha",
            "Intended Audience :: Developers",
            "Intended Audience :: Information Technology",
            "Intended Audience :: System Administrators",
            "License :: OSI Approved :: MIT License",
            "Operating System :: Unix",
            "Operating System :: POSIX :: Linux",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3 :: Only",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Topic :: Software Development :: Libraries :: Python Modules",
            "Topic :: Internet",
            "Typing :: Typed",
        ],
        description="Modern, container first framework for creating ready for production workflows.",
        include_package_data=True,
        install_requires=requirements.read(),
        license="MIT",
        long_description=readme.read(),
        long_description_content_type="text/markdown",
        name="laminar",
        packages=find_packages(exclude=["tests"]),
        python_requires=">=3.8",
        url="https://github.com/rchui/laminar",
        version=str(SourceFileLoader("version", VERSION).load_module().VERSION),
    )
