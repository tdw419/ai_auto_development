#!/usr/bin/env python3
"""Setup configuration for packaging legacy timezone utilities."""

from setuptools import setup

setup(
    name="vista-time-utils",
    version="1.0.0",
    packages=["utils"],
    package_dir={"": "../11"},
    python_requires=">=3.8",
)
