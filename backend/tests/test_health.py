from novestia.config import settings


def test_version() -> None:
    assert settings.version == "0.1.0"
