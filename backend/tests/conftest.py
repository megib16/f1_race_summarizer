import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)


import pytest


@pytest.fixture(autouse=True)
def no_network_in_unit_tests(monkeypatch):
    """Any unit test that reaches FastF1 or MultiViewer must stub it explicitly."""
    import fetcher

    def blocked(*args, **kwargs):
        raise RuntimeError("network access is blocked in unit tests; stub this call")

    monkeypatch.setattr(fetcher.fastf1, "get_session", blocked)
    monkeypatch.setattr(fetcher.fastf1, "get_event_schedule", blocked)
    monkeypatch.setattr(fetcher, "fetch_circuit_payload", blocked)
