from setuptools import setup

setup(
    name="gmail-labeler",
    version="1.0.0",
    packages=["gmail_labeler"],
    install_requires=[
        "google-auth-oauthlib",
        "google-auth-httplib2",
        "google-api-python-client",
        "python-dateutil",
        "wxPython",
    ],
    entry_points={
        "console_scripts": [
            "gmail-labeler=gmail_labeler_gui:main",
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A Gmail email organizer that automatically labels old unread emails",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/gmail-labeler",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
) 