from setuptools import setup, find_packages


def parse_requirements(filename):
    with open(filename, "r") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="hbo_bench",
    version="0.1",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,  # Включает данные пакета
    package_data={"hbo_bench": ["py.typed"]},  # Включает py.typed файл
    install_requires=parse_requirements("requirements.txt"),
)
