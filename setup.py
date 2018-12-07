import os
from setuptools import setup


with open(os.path.join('soil', 'VERSION')) as f:
    __version__ = f.readlines()[0].strip()
    assert __version__


def parse_requirements(filename):
    """ load requirements from a pip requirements file """
    with open(filename, 'r') as f:
        lineiter = list(line.strip() for line in f)
    return [line for line in lineiter if line and not line.startswith("#")]


install_reqs = parse_requirements("requirements.txt")
test_reqs = parse_requirements("test-requirements.txt")


setup(
    name='soil',
    packages=['soil'],  # this must be the same as the name above
    version=__version__,
    description=('An Agent-Based Social Simulator for Social Networks'),
    author='J. Fernando Sanchez',
    author_email='jf.sanchez@upm.es',
    url='https://github.com/gsi-upm/soil',  # use the URL to the github repo
    download_url='https://github.com/gsi-upm/soil/archive/{}.tar.gz'.format(
        __version__),
    keywords=['agent', 'social', 'simulator'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3'],
    install_requires=install_reqs,
    extras_require={
        'web': ['tornado']

    },
    tests_require=test_reqs,
    setup_requires=['pytest-runner', ],
    include_package_data=True,
    entry_points={
        'console_scripts':
        ['soil = soil.__init__:main',
        'soil-web = soil.web.__init__:main']
    })
