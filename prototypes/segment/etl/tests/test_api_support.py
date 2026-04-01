import os
import sys
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from openai import OpenAI

from components import utils


def test_get_model_client_api():
    with patch.dict(
        os.environ, {"API_KEY": "test_key", "API_BASE_URL": "http://test.url"}
    ):
        client, processor, device = utils.get_model_client("test-model", backend="api")
        assert client is not None
        assert processor is None
        assert device is None
        print("API backend test passed")


def test_get_model_client_local():
    # Mock AutoModelForCausalLM and AutoProcessor to avoid actual loading
    with (
        patch("components.utils.AutoModelForCausalLM") as mock_model,
        patch("components.utils.AutoProcessor") as mock_processor,
        patch("components.utils.get_torch_device", return_value="cpu"),
    ):
        client, processor, device = utils.get_model_client(
            "test-model", backend="local"
        )
        assert client is not None
        assert processor is not None
        assert device == "cpu"
        print("Local backend test passed")


def test_generate_caption_api_passes_seed(mocker):
    mock_client = MagicMock(spec=OpenAI)
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "A caption"
    mock_client.chat.completions.create.return_value = mock_response

    mocker.patch("components.utils.encode_image", return_value="base64data")

    utils.generate_caption(
        mock_client, "image.png", "prompt", model_name="gpt-4o", seed=42
    )

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs.get("seed") == 42


def test_generate_caption_api_default_seed(mocker):
    mock_client = MagicMock(spec=OpenAI)
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "A caption"
    mock_client.chat.completions.create.return_value = mock_response

    mocker.patch("components.utils.encode_image", return_value="base64data")

    utils.generate_caption(mock_client, "image.png", "prompt", model_name="gpt-4o")

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs.get("seed") == 42


def test_generate_caption_api_seed_none_omits_param(mocker):
    mock_client = MagicMock(spec=OpenAI)
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "A caption"
    mock_client.chat.completions.create.return_value = mock_response

    mocker.patch("components.utils.encode_image", return_value="base64data")

    utils.generate_caption(mock_client, "image.png", "prompt", model_name="gpt-4o", seed=None)

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert "seed" not in call_kwargs


if __name__ == "__main__":
    test_get_model_client_api()
    test_get_model_client_local()
