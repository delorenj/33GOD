"""Tests for Letta agent integration."""

from uuid import uuid4

import pytest

from src.letta_agent import LettaAgent


@pytest.mark.asyncio
async def test_letta_agent_initialization(mocker):
    """Test Letta agent initializes correctly."""
    mock_client = mocker.AsyncMock()
    mock_client.get.return_value.json.return_value = [
        {"id": "test-agent-id", "name": "tonny-voice-assistant"}
    ]

    mocker.patch("httpx.AsyncClient", return_value=mock_client)

    agent = LettaAgent()
    await agent.initialize()

    assert agent.agent_id == "test-agent-id"
    mock_client.get.assert_called_once_with("/api/agents")


@pytest.mark.asyncio
async def test_letta_agent_creates_new_agent(mocker):
    """Test Letta agent creates new agent if none exists."""
    mock_client = mocker.AsyncMock()
    mock_client.get.return_value.json.return_value = []  # No existing agents
    mock_client.post.return_value.json.return_value = {"id": "new-agent-id"}

    mocker.patch("httpx.AsyncClient", return_value=mock_client)

    agent = LettaAgent()
    await agent.initialize()

    assert agent.agent_id == "new-agent-id"
    assert mock_client.post.call_count == 1


@pytest.mark.asyncio
async def test_letta_agent_process_message(mocker):
    """Test Letta agent processes message and returns response."""
    mock_client = mocker.AsyncMock()
    mock_client.get.return_value.json.return_value = [
        {"id": "agent-123", "name": "tonny-voice-assistant"}
    ]
    mock_client.post.return_value.json.return_value = {
        "messages": [
            {"role": "user", "content": "What's the weather?"},
            {"role": "assistant", "content": "It's sunny today."},
        ]
    }

    mocker.patch("httpx.AsyncClient", return_value=mock_client)

    agent = LettaAgent()
    await agent.initialize()

    session_id = uuid4()
    response = await agent.process_message("What's the weather?", session_id)

    assert response.text == "It's sunny today."
    assert response.agent_id == "agent-123"
    assert response.session_id == session_id
    assert response.processing_time_ms > 0


@pytest.mark.asyncio
async def test_letta_agent_handles_no_response(mocker):
    """Test Letta agent handles case with no assistant response."""
    mock_client = mocker.AsyncMock()
    mock_client.get.return_value.json.return_value = [
        {"id": "agent-123", "name": "tonny-voice-assistant"}
    ]
    mock_client.post.return_value.json.return_value = {
        "messages": []  # No messages
    }

    mocker.patch("httpx.AsyncClient", return_value=mock_client)

    agent = LettaAgent()
    await agent.initialize()

    with pytest.raises(ValueError, match="No assistant response"):
        await agent.process_message("Test", uuid4())
