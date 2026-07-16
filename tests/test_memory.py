from app.memory import LocalMemoryStore, extract_explicit_preferences
from models.memory import MemoryObservation, PreferenceUpdate
from models.project import Project


def observation(key: str, value: str, confidence: float = 0.8) -> MemoryObservation:
    return MemoryObservation(
        kind="preference",
        key=key,
        value=value,
        confidence=confidence,
        evidence="test",
    )


def test_explicit_language_preference_is_extracted_without_model_help():
    observations = extract_explicit_preferences("我喜欢使用粤语作为创作语言")

    assert len(observations) == 1
    assert observations[0].key == "preferred_languages"
    assert observations[0].value == "粤语"
    assert observations[0].confidence == 0.85

    mixed = extract_explicit_preferences("以后默认做纯音乐，这次生成雨夜氛围电子曲")
    assert [(item.key, item.value) for item in mixed] == [
        ("vocal_preference", "纯音乐")
    ]


def test_memory_normalizes_reinforces_and_replaces_preferences(tmp_path):
    path = tmp_path / "memory" / "user_profile.json"
    store = LocalMemoryStore(path)

    store.merge_observations(
        [observation("default_instrumental", "以后默认生成纯音乐（无 vocal）")],
        session_id="session1",
    )
    reinforced = store.merge_observations(
        [observation("vocal_preference", "纯音乐", 0.9)],
        session_id="session2",
    )

    assert len(reinforced.preferences) == 1
    assert reinforced.preferences[0].key == "vocal_preference"
    assert reinforced.preferences[0].value == "纯音乐"
    assert reinforced.preferences[0].evidence_count == 2
    assert reinforced.preferences[0].source_session_ids == ["session1", "session2"]

    replaced = store.merge_observations(
        [observation("vocal_preference", "以后默认生成人声歌曲", 0.95)],
        session_id="session3",
    )
    assert len(replaced.preferences) == 1
    assert replaced.preferences[0].value == "人声歌曲"
    assert LocalMemoryStore(path).load_profile().preferences[0].value == "人声歌曲"


def test_explicit_project_controls_override_long_term_memory(tmp_path):
    store = LocalMemoryStore(tmp_path / "profile.json")
    store.merge_observations(
        [
            observation("vocal_preference", "纯音乐"),
            observation("preferred_genres", "电子"),
            observation("preferred_instruments", "合成器、钢琴"),
        ],
        session_id="session1",
    )

    automatic = store.resolve_preferences(Project(title="自动", user_request="创作音乐"))
    assert automatic.vocal is False
    assert automatic.genre == "电子"
    assert automatic.instruments == ["合成器", "钢琴"]
    assert automatic.sources["genre"] == "long_term_memory"

    current_request = store.resolve_preferences(
        Project(
            title="本次覆盖",
            user_request="这次做一首有人声和歌词的爵士歌曲，用电吉他",
        )
    )
    assert current_request.vocal is True
    assert current_request.genre == "爵士"
    assert current_request.instruments == ["电吉他"]
    assert current_request.sources["vocal"] == "current_request"

    explicit = store.resolve_preferences(
        Project(
            title="明确",
            user_request="创作歌曲",
            preset="pop_vocal",
            genre="摇滚",
            instruments=["电吉他"],
        )
    )
    assert explicit.vocal is True
    assert explicit.genre == "摇滚"
    assert explicit.instruments == ["电吉他"]
    assert explicit.sources["vocal"] == "project_preset"

    jazz = store.resolve_preferences(
        Project(title="爵士", user_request="创作爵士", preset="jazz_ensemble")
    )
    hiphop = store.resolve_preferences(
        Project(title="嘻哈", user_request="创作说唱", preset="hiphop_vocal")
    )
    assert jazz.vocal is False
    assert hiphop.vocal is True


def test_memory_preferences_can_be_edited_deleted_and_cleared(tmp_path):
    store = LocalMemoryStore(tmp_path / "profile.json")
    store.merge_observations(
        [observation("preferred_genres", "电子")],
        session_id="session1",
    )

    updated = store.update_preference(
        "preferred_genres",
        PreferenceUpdate(value="爵士", confidence=1.0),
    )
    assert updated.value == "爵士"
    assert store.delete_preference("preferred_genres").preferences == []

    store.record_workflow("pop_vocal")
    cleared = store.clear()
    assert cleared.preferences == []
    assert cleared.workflow_counts == {}
