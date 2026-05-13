from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _service_block(compose: str, service_name: str) -> str:
    pattern = rf"(?ms)^  {re.escape(service_name)}:\n(.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)"
    match = re.search(pattern, compose)
    if not match:
        raise AssertionError(f"Service block '{service_name}' not found in docker-compose.yml")
    return match.group(1)


class TestProwlarrVpnRouting(unittest.TestCase):
    def test_gluetun_publishes_prowlarr_port(self):
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        gluetun_block = _service_block(compose, "gluetun")
        self.assertIn("- 127.0.0.1:9696:9696", gluetun_block)

    def test_prowlarr_uses_gluetun_network_namespace(self):
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        prowlarr_block = _service_block(compose, "prowlarr")
        self.assertIn('network_mode: "service:gluetun"', prowlarr_block)

    def test_backend_default_prowlarr_url_targets_gluetun(self):
        config_py = (ROOT / "app" / "config.py").read_text(encoding="utf-8")
        self.assertIn('prowlarr_url: str = "http://gluetun:9696"', config_py)

    def test_env_example_default_prowlarr_url_targets_gluetun(self):
        env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("PROWLARR_URL=http://gluetun:9696", env_example)


if __name__ == "__main__":
    unittest.main()
