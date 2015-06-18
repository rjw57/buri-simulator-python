from setuptools import setup, find_packages

setup(
    name='burisim',
    version='0.1',
    description='Simulator for buri machine',
    author='Rich Wareham',
    author_email='rich.buri@richwareham.com',
    packages=find_packages(exclude=['tests', 'lib6502']),
    setup_requires=['cffi>=1.0.0'],
    cffi_modules=['burisim/_lib6502_build.py:ffi'],
    install_requires=[
        'cffi>=1.0.0',
        'docopt',
        'future',
        'intervaltree',
        'pyside',
        'pyte',
    ],
    entry_points={
        'console_scripts': [
            'burisim = burisim:main',
        ],
    },
)
