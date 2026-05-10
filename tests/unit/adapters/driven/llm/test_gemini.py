import pytest
from unittest.mock import MagicMock, patch
from adapters.driven.llm.gemini import GeminiAdapter

@pytest.fixture
def gemini_adapter():
    with patch("adapters.driven.llm.gemini.genai.Client") as mock_client:
        adapter = GeminiAdapter(api_key="test_key")
        adapter.client = mock_client
        yield adapter

@pytest.mark.asyncio
async def test_generate(gemini_adapter):
    mock_response = MagicMock()
    mock_response.text = "test response"
    gemini_adapter.client.models.generate_content.return_value = mock_response

    result = await gemini_adapter.generate("test prompt")
    
    assert result == "test response"
    gemini_adapter.client.models.generate_content.assert_called_once_with(
        model="gemini-2.0-flash",
        contents="test prompt"
    )

@pytest.mark.asyncio
async def test_embed(gemini_adapter):
    mock_response = MagicMock()
    mock_embedding = MagicMock()
    mock_embedding.values = [0.1, 0.2, 0.3]
    mock_response.embeddings = [mock_embedding]
    gemini_adapter.client.models.embed_content.return_value = mock_response

    result = await gemini_adapter.embed("test text")
    
    assert result == [0.1, 0.2, 0.3]
    gemini_adapter.client.models.embed_content.assert_called_once_with(
        model="text-embedding-004",
        contents="test text"
    )

def test_count_tokens(gemini_adapter):
    text = "one two three four"
    result = gemini_adapter.count_tokens(text)
    assert result == 8
