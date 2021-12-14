import setuptools

"""
Install locally:
>>> python setup.py install
"""

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


def read_requirements(fname):
    requirements = []
    with open(fname, "r") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            requirements.append(line)


setuptools.setup(
    name="DART-WRF",
    version="2021.12.14",
    author="Lukas Kugler",
    author_email="lukas.kugler@univie.ac.at",
    description="Observing system simulation experiments with WRF and DART",
    long_description=long_description,
    long_description_content_type="Markdown",
    url="https://github.com/lkugler/DART-WRF",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache 2.0 License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8.3",
    install_requires=read_requirements("environment.yml"),
)
