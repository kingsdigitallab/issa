import os
import sys
from unittest.mock import patch

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

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


if __name__ == "__main__":
    test_get_model_client_api()
    test_get_model_client_local()
