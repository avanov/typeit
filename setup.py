from pathlib import Path
from setuptools import setup
from setuptools import find_packages


here = Path(__file__).absolute().parent

with (here / 'README.rst').open() as f:
    README = f.read()

with (here / 'requirements.txt').open() as f:
    rows = f.read().strip().split('\n')
    requires = []
    for row in rows:
        row = row.strip()
        if row and not (row.startswith('#') or row.startswith('http')):
            requires.append(row)


# Setup
# ----------------------------

setup(name='typeit',
      version='0.6.0',
      description='Type it!',
      long_description=README,
      classifiers=[
          'Development Status :: 1 - Planning',
          'Intended Audience :: Developers',
          'License :: OSI Approved',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Operating System :: POSIX',
      ],
      author='Maxim Avanov',
      author_email='maxim.avanov@gmail.com',
      url='https://github.com/avanov/typeit',
      keywords='utils typing json yaml',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='tests',
      tests_require=['pytest', 'coverage'],
      install_requires=requires,
      entry_points={
          'console_scripts': [
              'typeit = typeit.cli:main'
          ],
      }
    )
