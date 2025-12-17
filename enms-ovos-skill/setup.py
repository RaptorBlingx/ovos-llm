#!/usr/bin/env python3
from setuptools import setup, find_packages
import os
from os import walk, path

# Package information
SKILL_CLAZZ = "create_skill"  # Factory function name
VERSION = "1.0.0"
URL = "https://github.com/aplusengineering/enms-ovos-skill"
AUTHOR = "A Plus Engineering"
EMAIL = "info@aplusengineering.com"
LICENSE = "GPL-3.0"
DESCRIPTION = "OVOS skill for industrial energy management (ISO 50001) - Voice assistant for manufacturing SMEs"

PYPI_NAME = "enms-ovos-skill"

# Construct entry point for plugin
SKILL_ID = f"{PYPI_NAME.lower()}.{AUTHOR.lower()}"
SKILL_PKG = PYPI_NAME.replace('-', '_')
# Entry point: 'skill.name=package_name:SkillClass'
PLUGIN_ENTRY_POINT = f"{SKILL_ID}={SKILL_PKG}:EnmsSkill"


def get_requirements(requirements_filename: str = "requirements.txt"):
    """Parse requirements from a file."""
    requirements_file = path.join(path.abspath(path.dirname(__file__)),
                                  requirements_filename)
    with open(requirements_file, 'r', encoding='utf-8') as r:
        requirements = r.readlines()
    requirements = [r.strip() for r in requirements if r.strip()
                    and not r.strip().startswith("#")]
    if 'MYCROFT_LOOSE_REQUIREMENTS' in os.environ:
        print('USING LOOSE REQUIREMENTS!')
        requirements = [r.replace('==', '>=').replace('~=', '>=') for r in requirements]
    return requirements


def find_resource_files():
    """Ensure all non-code resource files are included in the package"""
    resource_base_dirs = ("locale", "ui", "vocab", "dialog", "regex", "intent", "entities", "config", "models")
    base_dir = path.join(path.dirname(__file__), SKILL_PKG)
    package_data = ["*.json", "*.yaml", "*.md", "*.gguf"]
    for res in resource_base_dirs:
        if path.isdir(path.join(base_dir, res)):
            for (directory, _, files) in walk(path.join(base_dir, res)):
                if files:
                    package_data.append(
                        path.join(directory.replace(base_dir, "").lstrip('/'),
                                  '*'))
    return package_data


# Setup configuration
setup(
    name=PYPI_NAME,
    version=VERSION,
    description=DESCRIPTION,
    url=URL,
    author=AUTHOR,
    author_email=EMAIL,
    license=LICENSE,
    packages=find_packages(),
    package_data={SKILL_PKG: find_resource_files()},
    include_package_data=True,
    install_requires=get_requirements("requirements.txt"),
    keywords='ovos skill plugin energy management manufacturing iso50001 sme industry',
    entry_points={'ovos.plugin.skill': PLUGIN_ENTRY_POINT},
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Manufacturing',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3.10',
        'Topic :: Scientific/Engineering :: Energy Management',
        'Topic :: Office/Business :: Manufacturing',
    ],
    python_requires='>=3.10',
)
