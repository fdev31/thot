from setuptools import setup, find_packages

setup(
    name="thotus",
    version="0.1.0",
    author="Fabien Devaux",
    author_email="fdev31@gmail.com",
    license="MIT",
    platform="all",
    description="A 3D scanning application",
    long_description=open('README.md', encoding='utf-8').read(),
    scripts=['thot'],
    package_dir={'':'src'},
    packages=find_packages('src'),
    url='https://github.com/fdev31/thot',
#    zip_safe=False,
    keywords=[],
    install_requires=[
            'numpy >= 1.0.0 ',
        ],
    classifiers=[
        'Environment :: Console',
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ]
)
