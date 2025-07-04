from setuptools import setup, find_packages

setup(
    name="automation-jp-procurement-api",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "psycopg2-binary",
        "pgvector",
        "openai",
        "pydantic",
        "python-dotenv",
    ],
)