import json

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.routes.slack import router as slack_router
from api.slack_adapter import SlackRequestValidator
from core.decorators import must_stay_async


class FakeRateLimiter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    @must_stay_async("callers use await")
    async def check_and_increment(self, rate_key: str, limit: int) -> bool:
        self.calls.append((rate_key, limit))
        return True


def _build_app(signing_secret: str) -> FastAPI:
    app = FastAPI()
    app.include_router(slack_router)
    app.state.slack_validator = SlackRequestValidator(signing_secret)
    return app


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_slack_events_ack_success_with_rate_limiter(
    monkeypatch,
    slack_signing_secret,
    slack_signature_generator,
    fresh_slack_timestamp,
):
    app = _build_app(slack_signing_secret)
    app.state.rate_limiter = FakeRateLimiter()

    @must_stay_async("callers use await")
    async def fake_handle_slack_events(**_kwargs):
        return {"ok": True}

    monkeypatch.setattr(
        "api.routes.slack.handle_slack_events", fake_handle_slack_events
    )

    payload = {
        "type": "event_callback",
        "event_id": "Ev123",
        "team_id": "T123",
        "event": {
            "type": "app_mention",
            "user": "U123",
            "channel": "C123",
            "text": "hello",
            "ts": "123.456",
        },
    }
    body = json.dumps(payload)
    signature = slack_signature_generator(
        body, fresh_slack_timestamp, slack_signing_secret
    )
    headers = {
        "X-Slack-Signature": signature,
        "X-Slack-Request-Timestamp": fresh_slack_timestamp,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/slack/events", content=body, headers=headers)

    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_slack_events_failure_surfaces_to_slack(
    monkeypatch,
    slack_signing_secret,
    slack_signature_generator,
    fresh_slack_timestamp,
):
    app = _build_app(slack_signing_secret)

    @must_stay_async("callers use await")
    async def fake_handle_slack_events(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "api.routes.slack.handle_slack_events", fake_handle_slack_events
    )

    payload = {
        "type": "event_callback",
        "event_id": "Ev456",
        "team_id": "T123",
        "event": {
            "type": "app_mention",
            "user": "U456",
            "channel": "C123",
            "text": "hello",
            "ts": "123.456",
        },
    }
    body = json.dumps(payload)
    signature = slack_signature_generator(
        body, fresh_slack_timestamp, slack_signing_secret
    )
    headers = {
        "X-Slack-Signature": signature,
        "X-Slack-Request-Timestamp": fresh_slack_timestamp,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/slack/events", content=body, headers=headers)

    assert response.status_code == 500
    assert response.json()["detail"] == "Slack event processing failed"
