"""Test for laminar.configurations.flows"""

import pytest

from laminar.configurations import flows
from laminar.configurations.datastores import Memory
from laminar.exceptions import FlowError


class TestConfiguration:
    def test_error(self) -> None:
        with pytest.raises(FlowError):
            flows.Configuration(datastore=Memory())
