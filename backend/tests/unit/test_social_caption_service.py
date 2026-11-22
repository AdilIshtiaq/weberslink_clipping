import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.services import social_caption_service as pack_service
from src.services.social_caption_service import MusicSuggestion, PostPack


def make_pack(**overrides):
    values = dict(
        caption="  Watch this idea.  ",
        hashtags=["#Podcast", "podcast", " clips ", "two words", "", "#" + "x" * 80, "Growth_Tips"],
        location="  Lahore,   Pakistan ",
        music=MusicSuggestion(style=" calm   lo-fi ", tip="Keep it quiet under speech"),
        why_viral="Opens on a bold claim.",
        mentions=["@WebersLink", "stranger", "weberslink"],
    )
    values.update(overrides)
    return PostPack(**values)


def test_normalize_handles_cleans_and_dedupes():
    assert pack_service.normalize_handles(["@WebersLink", "weberslink", " a.b_c ", "bad handle", "", "@x" * 20]) == [
        "WebersLink", "a.b_c",
    ]
    assert pack_service.normalize_handles(None) == []


def test_finalize_cleans_every_field():
    result = pack_service.finalize_post_pack(make_pack(), ["WebersLink"])
    assert result["caption"] == "Watch this idea."
    assert result["hashtags"] == ["Podcast", "clips", "Growth_Tips"]
    assert result["location"] == "Lahore, Pakistan"
    assert result["music"] == {"style": "calm lo-fi", "tip": "Keep it quiet under speech"}
    assert result["why_viral"] == "Opens on a bold claim."
    # Only handles from the user's list survive, copied in the user's spelling.
    assert result["mentions"] == ["@WebersLink"]


def test_mentions_are_never_invented():
    result = pack_service.finalize_post_pack(make_pack(mentions=["@someone_else"]), [])
    assert result["mentions"] == []


def test_mentions_are_capped_at_three():
    handles = ["a", "b", "c", "d", "e"]
    result = pack_service.finalize_post_pack(make_pack(mentions=handles), handles)
    assert result["mentions"] == ["@a", "@b", "@c"]


@pytest.mark.parametrize("caption", [" ", "x" * 2201])
def test_rejects_invalid_caption(caption):
    with pytest.raises(ValueError):
        pack_service.finalize_post_pack(make_pack(caption=caption), [])


async def test_generate_uses_grounded_clip_data_and_the_given_model(monkeypatch):
    run = AsyncMock(return_value=SimpleNamespace(output=make_pack()))
    seen = {}

    def agent(model, **kwargs):
        seen["model"] = model
        seen.update(kwargs)
        return SimpleNamespace(run=run)

    monkeypatch.setattr(pack_service, "Agent", agent)
    result = await pack_service.generate_post_pack(
        "test-model", {"hook_title": "An idea", "text": "A real transcript"}, "instagram", ["@WebersLink", "bad handle"]
    )
    assert seen["model"] == "test-model"
    assert seen["output_type"] is PostPack
    assert json.loads(run.await_args.args[0]) == {
        "platform": "instagram", "headline": "An idea", "transcript": "A real transcript",
        "allowed_mentions": ["@WebersLink"],
    }
    assert result["mentions"] == ["@WebersLink"]
