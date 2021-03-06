from distutils.command.clean import clean
from setuptools import setup, find_packages
from setuptools.command.install import install


class CleanInstall(install):
    def run(self):
        super(CleanInstall, self).run()
        c = clean(self.distribution)
        c.all = True
        c.finalize_options()
        c.run()


setup(
    name='weaveserver',
    version='0.8',
    author='Srivatsan Iyer',
    author_email='supersaiyanmode.rox@gmail.com',
    packages=find_packages(),
    license='MIT',
    description='Library to interact with Weave Server',
    long_description=open('README.md').read(),
    install_requires=[
        'weavelib',
        'eventlet!=0.22',
        'bottle',
        'GitPython',
        'redis',
        'appdirs',
        'peewee',
        'virtualenv',
        'github3.py',
    ],
    entry_points={
        'console_scripts': [
            'weave-launch = app:handle_launch',
            'weave-main = app:handle_main'
        ]
    },
    cmdclass={'install': CleanInstall}
)
