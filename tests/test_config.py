from app.config import Settings


def test_cors_origins_are_normalized() -> None:
    settings = Settings(cors_origins="http://localhost:5173, http://localhost:3000")
    assert settings.cors_origin_list == ["http://localhost:5173", "http://localhost:3000"]
