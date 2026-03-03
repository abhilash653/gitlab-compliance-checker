from setuptools import setup, find_packages

# Read requirements from requirements.txt
with open("requirements.txt", "r") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="gitlab-compliance-checker",
    version="1.0.0",
    description="A Streamlit web application to verify GitLab project best practices and check user profile README status.",
    author="",
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.11",
)
