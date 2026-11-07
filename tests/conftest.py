import pytest

from edu_data.agregados import cargar_largo


@pytest.fixture(scope="session")
def largo():
    return cargar_largo()
