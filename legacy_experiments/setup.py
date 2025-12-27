import setuptools

setuptools.setup(
    name='credit-score-mvp',
    version='1.0',
    install_requires=[
        'google-cloud-documentai',
        'google-cloud-storage',
        'google-cloud-bigquery'
    ],
    packages=setuptools.find_packages(),
)
