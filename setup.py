from setuptools import setup

setup(name='curve_storage',
      version='1.0',
      description='Curve Database manager with a GUI',
      author='Thibault CAPELLE',
      author_email='capelle_thibault@riseup.net',
      include_package_data=True,
      package_data={'curve_storage': ['pictures/*.png']},
      packages=['curve_storage'],
	  package_dir={'curve_storage': 'curve_storage'}
     )
