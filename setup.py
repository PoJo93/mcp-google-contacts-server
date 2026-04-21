from setuptools import setup, find_packages

setup(
    name="mcp-google-contacts-server",
    version="0.2.0",
    description="FastMCP server for Google Contacts with optional Google OAuth gating",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Rayan Zaki",
    author_email="rayan.hassici@ensia.edu.dz",
    url="https://github.com/rayanzaki/mcp-google-contacts-server",
    packages=find_packages(),
    install_requires=[
        "fastmcp>=2.12",
        "google-api-python-client",
        "google-auth",
        "google-auth-oauthlib",
        "httpx",
        "pydantic",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.12",
    entry_points={
        "console_scripts": [
            "mcp-google-contacts=mcp_google_contacts_server.main:main",
        ],
    },
)
