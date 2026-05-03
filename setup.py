from setuptools import setup, find_packages

setup(
    name="zfc_leanpy",
    version="0.1",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[],
    author="",
    description="Lean互換・ZFC集合論ベース定理証明支援系",
)
