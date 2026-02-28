import pytest


def pytest_addoption(parser):
    """
    Add custom command-line options for pytest.
    """
    parser.addoption(
        "--code_version", action="store", default=None, help="Code version for the test"
    )


@pytest.fixture
def code_version(request):
    """
    Provide the --code_version argument as a fixture.
    """
    return request.config.getoption("--code_version")
