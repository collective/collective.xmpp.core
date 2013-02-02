from setuptools import setup, find_packages
import os

version = '0.1b5.dev0'

setup(name='collective.xmpp.core',
      version=version,
      description="Enables core functionality for XMPP-enabled Plone add-ons.",
      long_description=open("README.rst").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: Plone",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        ],
      keywords='plone xmpp twisted microblogging',
      author='Yiorgis Gozadinos',
      author_email='ggozad@crypho.com',
      url='https://github.com/collective/collective.xmpp.core',
      license='GPL',
      packages=find_packages(),
      namespace_packages=['collective', 'collective.xmpp'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'BeautifulSoup',
          'Twisted',
          'wokkel>0.6.3',
          'Products.UserAndGroupSelectionWidget',
          'jarn.jsi18n'
      ],
      extras_require = {
          'test': [
                  'plone.app.testing',
              ]
      },
      entry_points="""
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
