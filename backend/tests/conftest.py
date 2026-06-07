import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    mock_client = MagicMock()
    mock_client.close = MagicMock()
    with patch("app.core.database.init_db", new_callable=AsyncMock, return_value=mock_client):
        with patch("app.workers.mqtt_client.start_mqtt_worker", new_callable=AsyncMock):
            from app.main import app
            with TestClient(app) as c:
                yield c
