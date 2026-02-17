"""Package setup for Agentic Browser."""

from setuptools import setup, find_packages
from pathlib import Path

readme = Path("README.md").read_text(encoding="utf-8")

setup(
    name="agentic-browser",
    version="0.1.0",
    description="Secure, undetectable, AI-controlled browser system",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Dualios",
    url="https://github.com/dualios-dev/agentic-browser",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "": ["web/*", "config.yaml"],
    },
    python_requires=">=3.10",
    install_requires=[
        "camoufox[geoip]",
        "playwright",
        "beautifulsoup4",
        "markdownify",
        "pyyaml",
        "httpx",
        "fastapi",
        "uvicorn[standard]",
        "websockets",
    ],
    entry_points={
        "console_scripts": [
            "agentic-browser=src.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
