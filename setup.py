from setuptools import setup

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="shromazdeni",
    version="0.1",
    description="Module for voting on czech gatherings of building owners",
    author="Frantisek Jahoda",
    author_email="frantisek.jahoda@gmail.com",
    packages=["shromazdeni"],  # same as name
    install_requires=requirements,  # external packages as dependencies
)
