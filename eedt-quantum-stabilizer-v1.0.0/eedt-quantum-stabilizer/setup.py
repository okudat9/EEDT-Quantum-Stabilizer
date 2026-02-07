"""
EEDT Setup Configuration
=========================
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="eedt-quantum-stabilizer",
    version="1.0.0",
    author="093 (T.OKUDA)",
    author_email="o93dice@gmail.com",
    description="AI-Orchestrated Quantum Error Mitigation Middleware",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/093dice/eedt-quantum-stabilizer",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Physics",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.9",
    install_requires=[
        "numpy>=1.24.0",
        "scipy>=1.10.0",
        "matplotlib>=3.7.0",
        "pandas>=2.0.0",
        "qiskit>=1.0.0",
        "qiskit-ibm-runtime>=0.20.0",
        "qiskit-aer>=0.13.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
        ],
        "docs": [
            "sphinx>=6.0.0",
            "sphinx-rtd-theme>=1.2.0",
        ],
        "notebooks": [
            "jupyter>=1.0.0",
            "plotly>=5.18.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "eedt-validate=experiments.example_60_degree:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/093dice/eedt-quantum-stabilizer/issues",
        "Source": "https://github.com/093dice/eedt-quantum-stabilizer",
    },
)
