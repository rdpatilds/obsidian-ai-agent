"""End-to-end test for calculator tool via OpenAI API."""

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.shared.config import settings


pytestmark = pytest.mark.skipif(
    not settings.openai_api_key
    or settings.openai_api_key == ""
    or settings.openai_api_key.startswith("sk-test")
    or settings.openai_api_key.startswith("sk-your-"),
    reason="Requires valid OpenAI API key for end-to-end testing",
)


@pytest.mark.integration
def test_calculator_addition_non_streaming() -> None:
    """Test calculator addition via OpenAI API (non-streaming)."""
    client = TestClient(app)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "What is 25 plus 17?"}],
            "stream": False,
        },
        headers={"Authorization": f"Bearer {settings.openai_compatible_api_key}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "chat.completion"
    assert len(data["choices"]) > 0
    assert (
        "42" in data["choices"][0]["message"]["content"]
        or "25 + 17" in data["choices"][0]["message"]["content"]
    )


@pytest.mark.integration
def test_calculator_division_streaming() -> None:
    """Test calculator division via OpenAI API (streaming)."""
    client = TestClient(app)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Divide 100 by 4"}],
            "stream": True,
        },
        headers={"Authorization": f"Bearer {settings.openai_compatible_api_key}"},
    )

    assert response.status_code == 200

    # Verify streaming format
    content = response.text
    assert "data:" in content
    assert "[DONE]" in content


@pytest.mark.integration
def test_calculator_multi_turn_conversation() -> None:
    """Test calculator with conversation history."""
    client = TestClient(app)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": "What is 10 times 5?"},
                {"role": "assistant", "content": "10 * 5 = 50"},
                {"role": "user", "content": "Now add 25 to that result"},
            ],
            "stream": False,
        },
        headers={"Authorization": f"Bearer {settings.openai_compatible_api_key}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert (
        "75" in data["choices"][0]["message"]["content"]
        or "50 + 25" in data["choices"][0]["message"]["content"]
    )
