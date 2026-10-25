import pytest

from app.config import settings
from app.models import Mission
from app.services.context import collect_context


@pytest.mark.asyncio
async def test_event_mission_collects_the_specific_pull_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "integration_mode", "mock")
    mission = Mission(
        prompt="Review the pull request",
        project_name="General",
        source_context={
            "provider": "github",
            "repository": "acme/service",
            "pull_request_number": 7,
        },
    )

    context = await collect_context(mission)

    pull = next(item for item in context.evidence if item.provider.value == "github")
    assert pull.key == "github:pull_request:7"
    assert pull.external_id == "mock-pr-7"
    assert pull.title == "Mock PR #7"
    assert any(item.key.endswith(":files") for item in context.evidence)
    assert any(item.key.endswith(":commits") for item in context.evidence)
