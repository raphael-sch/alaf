from setuptools import setup, find_packages

setup(
    name='alafclient',
    version='0.0.2',
    url='https://github.com/raphael-sch/alaf',
    author='Raphael Schumann',
    author_email='rschuman@cl.uni-heidelberg.de',
    description='ALAF - Active Learning Annotation Framework',
    packages=find_packages(),
    install_requires=['socketIO-client==0.7.2'],
)
