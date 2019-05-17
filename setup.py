import os
import configparser
from setuptools import setup, find_packages
from setuptools.command.install import install

BASE_DIR = os.path.dirname(os.path.realpath(__file__))

class BuildCommand(install):
    """
    Build cp2trans with config prompt.
    """

    def run(self):
        language = None
        while language not in ('en', 'zh-CN'):
            language = input('Set application language [en/zh-CN]: ')
        appid = input('Your Youdao APPID: ')
        secretkey = input('Your Youdao APP secret: ')
        neologd = input('Your neologd dictionary path: ')
        config = configparser.ConfigParser()
        if not os.path.isfile(os.path.join(BASE_DIR, 'config.example.ini')):
            print('"config.example.ini" not found. Exit.')
            exit(-1)
        config.read(os.path.join(BASE_DIR, 'config.example.ini'))
        config.set('global', 'language', language)
        config.set('global', 'appid', appid)
        config.set('global', 'secretkey', secretkey)
        config.set('global', 'neologd', neologd)
        config.set('global', 'log_level', '20')
        with open(os.path.join(BASE_DIR, 'cp2trans', 'config.ini'), 'w') as f:
            config.write(f)
        install.do_egg_install(self)
        print('You can edit configurations in "config.ini" from directory '
              '"PYTHON_HOME\\Lib\\site-packages\cp2trans-*-*.egg\\cp2trans\\".')
        print('Please perform some post-install steps follow the instructions on "README.md"'
              ' from https://github.com/EnderQIU/ppat to complete the install process.')


install_requires = []

with open(os.path.join(BASE_DIR, 'requirements.txt'), encoding='utf8') as f:
    install_requires = f.read().splitlines()

README = ''

with open(os.path.join(BASE_DIR, 'README.md'), encoding='utf8') as f:
    README = f.read()

setup(name='cp2trans',
      version='1.0',
      description='Clipboard to translate.',
      long_description=README,
      long_description_content_type="text/markdown",
      keywords='clipboard translate',
      author='EnderQIU',
      author_email='a934560824@gmail.com',
      license='GPLv3',
      url='https://github.com/EnderQIU/cp2translate',
      install_requires=install_requires,
      packages=['cp2trans'],
      entry_points={
          'console_scripts': [
              'cp2trans = cp2trans.cp2trans:main',
          ],
      },
      include_package_data=True,
      cmdclass={'install': BuildCommand},
      classifiers=[
        'Development Status :: 4 - Beta',
        'Operating System :: Microsoft :: Windows :: Windows 10',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Utilities'
    ],
)
