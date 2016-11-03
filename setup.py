from setuptools import setup, find_packages, Extension

setup(
    name="thotus",
    version="0.1.1",
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
            'scipy >= 0.10.0',
            'numpy >= 1.0.0 ',
            'prompt-toolkit >= 1.0.0',
            'pyserial >= 3.0.0',
#            'v4l2capture 16.10.0',
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
    ],
    ext_modules= [
        Extension("v4l2capture", ["v4l2capture.c"],
        libraries=["v4l2"], extra_compile_args=['-DUSE_LIBV4L', ],
        )]

)
