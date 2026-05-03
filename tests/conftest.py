import pytest

from zfc_leanpy import dsl


@pytest.fixture(autouse=True)
def clear_registry():
    dsl.reset_registry()
    yield
    dsl.reset_registry()
