from setuptools import setup, find_packages


# pragma: no cover
def parse_requirements(filename):
    with open(filename, "r") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


setup(
    name="hbo_bench",
    version="0.1",
    packages=find_packages(),
    install_requires=parse_requirements("requirements.txt"),
)
