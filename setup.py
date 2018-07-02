"""test and build the package"""

import setuptools
from Cython import Build


def main():
    """main cli entrypoint"""
    setuptools.setup(
        name='hashmap',
        version='0.1',
        description='hash tables and filters',
        author='jake wires',
        author_email='jtwires@gmail.com',
        packages=setuptools.find_packages(exclude=['test.*']),
        install_requires=[
            'xxhash',
        ],
        setup_requires=[
            'pytest-runner',
            'pytest-pylint',
            'pytest-flake8',
        ],
        tests_require=[
            'pytest',
            'pylint',
            'flake8',
        ],
        test_suite='setup.test_suite',
        ext_modules=Build.cythonize('hashmap/*.pyx'),
    )


if __name__ == '__main__':
    main()
