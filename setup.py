import pip
from setuptools import setup
# parse_requirements() returns generator of pip.req.InstallRequirement objects
from pip.req import parse_requirements
from soil import __version__

try:
    install_reqs = parse_requirements(
        "requirements.txt", session=pip.download.PipSession())
    test_reqs = parse_requirements(
        "test-requirements.txt", session=pip.download.PipSession())
except AttributeError:
    install_reqs = parse_requirements("requirements.txt")
    test_reqs = parse_requirements("test-requirements.txt")

install_reqs = [str(ir.req) for ir in install_reqs]
test_reqs = [str(ir.req) for ir in test_reqs]


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
    classifiers=[],
    install_requires=install_reqs,
    tests_require=test_reqs,
    setup_requires=['pytest-runner', ],
    include_package_data=True,
    entry_points={
        'console_scripts':
        ['soil = soil.__init__:main']
    })
