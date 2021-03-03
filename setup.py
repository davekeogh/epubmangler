from setuptools import setup

setup(
    name='epubmangler',
    version='0.1.0',
    py_modules=['epubmangler'],
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        epubmangler=epubmangler:command_line
    ''',
)
