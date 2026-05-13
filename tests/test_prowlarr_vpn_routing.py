from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TestProwlarrVpnRouting(unittest.TestCase):
    def test_gluetun_publishes_prowlarr_port(self):
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("- 127.0.0.1:9696:9696", compose)

    def test_prowlarr_uses_gluetun_network_namespace(self):
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn('network_mode: "service:gluetun"', compose)

    def test_backend_default_prowlarr_url_targets_gluetun(self):
        config_py = (ROOT / "app" / "config.py").read_text(encoding="utf-8")
        self.assertIn('prowlarr_url: str = "http://gluetun:9696"', config_py)

    def test_env_example_default_prowlarr_url_targets_gluetun(self):
        env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("PROWLARR_URL=http://gluetun:9696", env_example)


if __name__ == "__main__":
    unittest.main()
