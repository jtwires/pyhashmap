import setuptools

def test_suite():
    import unittest
    return unittest.TestLoader().discover('test', pattern='*.py')

def main():
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
        test_suite='setup.test_suite',
    )

if __name__ == '__main__':
    main()
