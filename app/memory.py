from pathlib import Path
import re
from threading import RLock

from models.memory import (
    EffectiveCreativePreferences,
    MemoryContext,
    MemoryObservation,
    PortfolioItem,
    PreferenceUpdate,
    UserPreference,
    UserProfile,
)
from models.project import Project, utc_now

CANONICAL_KEYS = {
    "vocal_preference",
    "preferred_genres",
    "preferred_languages",
    "preferred_instruments",
    "avoided_instruments",
    "default_duration",
    "production_style",
}
KEY_ALIASES = {
    "default_instrumental": "vocal_preference",
    "instrumental_preference": "vocal_preference",
    "no_vocals": "vocal_preference",
    "default_genre": "preferred_genres",
    "genre_preference": "preferred_genres",
    "default_language": "preferred_languages",
    "language_preference": "preferred_languages",
    "default_instruments": "preferred_instruments",
    "instrument_preference": "preferred_instruments",
}


class MemoryNotFoundError(KeyError):
    pass


def canonical_key(key: str) -> str | None:
    normalized = key.strip().lower()
    normalized = KEY_ALIASES.get(normalized, normalized)
    return normalized if normalized in CANONICAL_KEYS else None


def normalized_value(key: str, value: str) -> str:
    cleaned = " ".join(value.strip().split())
    if key == "vocal_preference":
        lowered = cleaned.lower()
        if any(token in lowered for token in ("纯音乐", "无人声", "无 vocal", "instrumental", "no vocal")):
            return "纯音乐"
        if any(token in lowered for token in ("人声", "演唱", "vocal")):
            return "人声歌曲"
    return cleaned


def split_values(value: str) -> list[str]:
    normalized = value
    for separator in ("，", "、", ";", "；", "/", "|"):
        normalized = normalized.replace(separator, ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def first_match(text: str, choices: dict[str, tuple[str, ...]]) -> str | None:
    lowered = text.lower()
    return next(
        (value for value, markers in choices.items() if any(marker in lowered for marker in markers)),
        None,
    )


def extract_explicit_preferences(text: str) -> list[MemoryObservation]:
    signal_markers = ("喜欢", "偏好", "以后", "默认", "通常", "习惯", "一直")
    clauses = [clause.strip() for clause in re.split(r"[，,。；;！？!?\n]+", text)]
    preference_clauses = [
        clause for clause in clauses if any(marker in clause.lower() for marker in signal_markers)
    ]
    if not preference_clauses:
        return []

    preference_text = "，".join(preference_clauses)
    lowered = preference_text.lower()
    confidence = 0.95 if any(marker in lowered for marker in ("以后", "默认", "一直")) else 0.85
    observations: list[MemoryObservation] = []
    language = first_match(
        lowered,
        {
            "中文": ("中文", "国语", "普通话"),
            "粤语": ("粤语", "广东话"),
            "英文": ("英文", "英语", "english"),
            "日语": ("日语", "日文", "japanese"),
            "韩语": ("韩语", "韩文", "korean"),
            "西班牙语": ("西班牙语", "spanish"),
        },
    )
    if language and any(marker in lowered for marker in ("语言", "歌词", "演唱", "唱")):
        observations.append(
            MemoryObservation(
                kind="preference",
                key="preferred_languages",
                value=language,
                confidence=confidence,
                evidence=text,
            )
        )

    if any(marker in lowered for marker in ("纯音乐", "无人声", "无 vocal", "instrumental", "no vocal")):
        observations.append(
            MemoryObservation(
                kind="preference",
                key="vocal_preference",
                value="纯音乐",
                confidence=confidence,
                evidence=text,
            )
        )
    elif any(marker in lowered for marker in ("人声歌曲", "有人声", "带人声")):
        observations.append(
            MemoryObservation(
                kind="preference",
                key="vocal_preference",
                value="人声歌曲",
                confidence=confidence,
                evidence=text,
            )
        )

    genre = first_match(
        lowered,
        {
            "流行": ("流行", "pop"),
            "摇滚": ("摇滚", "rock"),
            "电子": ("电子", "electronic"),
            "R&B": ("r&b", "节奏布鲁斯"),
            "爵士": ("爵士", "jazz"),
            "古典": ("古典", "classical"),
            "民谣": ("民谣", "folk"),
            "嘻哈": ("嘻哈", "hip-hop", "hip hop"),
            "影视配乐": ("影视配乐", "电影配乐", "soundtrack"),
        },
    )
    if genre and any(marker in lowered for marker in ("流派", "风格", "音乐")):
        observations.append(
            MemoryObservation(
                kind="preference",
                key="preferred_genres",
                value=genre,
                confidence=confidence,
                evidence=text,
            )
        )

    instruments = [
        instrument
        for instrument in ("钢琴", "原声吉他", "电吉他", "弦乐", "管弦乐", "合成器", "鼓组", "贝斯", "民族乐器")
        if instrument in preference_text
    ]
    if instruments:
        observations.append(
            MemoryObservation(
                kind="preference",
                key="preferred_instruments",
                value="、".join(instruments),
                confidence=confidence,
                evidence=text,
            )
        )
    return observations


class LocalMemoryStore:
    def __init__(self, path: Path | str = "data/memory/user_profile.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def load_profile(self) -> UserProfile:
        if not self.path.is_file():
            return UserProfile()
        profile = UserProfile.model_validate_json(self.path.read_text(encoding="utf-8"))
        normalized: dict[str, UserPreference] = {}
        for preference in profile.preferences:
            key = canonical_key(preference.key)
            if key is None:
                continue
            preference.key = key
            preference.value = normalized_value(key, preference.value)
            existing = normalized.get(key)
            if existing is None or preference.last_seen_at >= existing.last_seen_at:
                normalized[key] = preference
        profile.preferences = list(normalized.values())
        return profile

    def merge_observations(
        self,
        observations: list[MemoryObservation],
        *,
        session_id: str,
    ) -> UserProfile:
        with self._lock:
            profile = self.load_profile()
            for observation in observations:
                key = canonical_key(observation.key)
                if key is None:
                    continue
                value = normalized_value(key, observation.value)
                existing = next(
                    (
                        preference
                        for preference in profile.preferences
                        if preference.key == key and preference.value == value
                    ),
                    None,
                )
                if existing is None:
                    profile.preferences.append(
                        UserPreference(
                            kind=observation.kind,
                            key=key,
                            value=value,
                            confidence=observation.confidence,
                            source_session_ids=[session_id],
                        )
                    )
                    profile.preferences = [
                        preference
                        for preference in profile.preferences
                        if preference.key != key or preference.value == value
                    ]
                    continue
                existing.evidence_count += 1
                existing.confidence = min(
                    1.0,
                    max(existing.confidence, observation.confidence)
                    + 0.08 * (1 - existing.confidence),
                )
                existing.last_seen_at = utc_now()
                if session_id not in existing.source_session_ids:
                    existing.source_session_ids.append(session_id)
            profile.updated_at = utc_now()
            self.save_profile(profile)
            return profile

    def update_preference(self, key: str, data: PreferenceUpdate) -> UserPreference:
        normalized_key = canonical_key(key)
        if normalized_key is None:
            raise MemoryNotFoundError(key)
        with self._lock:
            profile = self.load_profile()
            preference = next(
                (item for item in profile.preferences if item.key == normalized_key),
                None,
            )
            if preference is None:
                raise MemoryNotFoundError(key)
            preference.kind = data.kind
            preference.value = normalized_value(normalized_key, data.value)
            preference.confidence = data.confidence
            preference.last_seen_at = utc_now()
            profile.updated_at = utc_now()
            self.save_profile(profile)
            return preference

    def delete_preference(self, key: str) -> UserProfile:
        normalized_key = canonical_key(key)
        if normalized_key is None:
            raise MemoryNotFoundError(key)
        with self._lock:
            profile = self.load_profile()
            remaining = [item for item in profile.preferences if item.key != normalized_key]
            if len(remaining) == len(profile.preferences):
                raise MemoryNotFoundError(key)
            profile.preferences = remaining
            profile.updated_at = utc_now()
            self.save_profile(profile)
            return profile

    def clear(self) -> UserProfile:
        profile = UserProfile()
        self.save_profile(profile)
        return profile

    def record_workflow(self, preset: str) -> UserProfile:
        with self._lock:
            profile = self.load_profile()
            profile.workflow_counts[preset] = profile.workflow_counts.get(preset, 0) + 1
            profile.updated_at = utc_now()
            self.save_profile(profile)
            return profile

    def save_profile(self, profile: UserProfile) -> None:
        temporary = self.path.with_suffix(".json.tmp")
        with self._lock:
            temporary.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
            temporary.replace(self.path)

    def context(self, projects: list[Project], limit: int = 20) -> MemoryContext:
        profile = self.load_profile()
        return MemoryContext(
            preferences=sorted(
                profile.preferences,
                key=lambda item: (item.confidence, item.evidence_count),
                reverse=True,
            ),
            workflow_counts=profile.workflow_counts,
            previous_works=[self.portfolio_item(project) for project in projects[:limit]],
        )

    def resolve_preferences(self, project: Project) -> EffectiveCreativePreferences:
        profile = self.load_profile()
        preferences = {item.key: item for item in profile.preferences if item.confidence >= 0.55}
        resolved = EffectiveCreativePreferences()

        request = project.user_request.lower()
        if project.preset in {"pop_vocal", "rock_vocal", "folk_acoustic", "hiphop_vocal"}:
            resolved.vocal = True
            resolved.sources["vocal"] = "project_preset"
        elif project.preset in {
            "classical_instrumental",
            "electronic_instrumental",
            "soundtrack_score",
            "jazz_ensemble",
        }:
            resolved.vocal = False
            resolved.sources["vocal"] = "project_preset"
        elif any(marker in request for marker in ("纯音乐", "无人声", "无 vocal", "instrumental", "no vocal")):
            resolved.vocal = False
            resolved.sources["vocal"] = "current_request"
        elif any(marker in request for marker in ("人声", "演唱", "歌词", "vocal")):
            resolved.vocal = True
            resolved.sources["vocal"] = "current_request"
        elif preference := preferences.get("vocal_preference"):
            resolved.vocal = preference.value == "人声歌曲"
            resolved.sources["vocal"] = "long_term_memory"

        if project.genre != "auto":
            resolved.genre = project.genre
            resolved.sources["genre"] = "project_control"
        elif genre := first_match(
            request,
            {
                "流行": ("流行", "pop"),
                "摇滚": ("摇滚", "rock"),
                "电子": ("电子", "electronic"),
                "R&B": ("r&b", "节奏布鲁斯"),
                "爵士": ("爵士", "jazz"),
                "古典": ("古典", "classical"),
                "民谣": ("民谣", "folk"),
                "嘻哈": ("嘻哈", "hip-hop", "hip hop"),
                "影视配乐": ("影视配乐", "电影配乐", "soundtrack"),
            },
        ):
            resolved.genre = genre
            resolved.sources["genre"] = "current_request"
        elif preference := preferences.get("preferred_genres"):
            resolved.genre = split_values(preference.value)[0]
            resolved.sources["genre"] = "long_term_memory"

        if project.language != "auto":
            resolved.language = project.language
            resolved.sources["language"] = "project_control"
        elif language := first_match(
            request,
            {
                "中文": ("中文", "国语", "普通话"),
                "粤语": ("粤语", "广东话"),
                "英文": ("英文", "英语", "english"),
                "日语": ("日语", "日文", "japanese"),
                "韩语": ("韩语", "韩文", "korean"),
                "西班牙语": ("西班牙语", "spanish"),
            },
        ):
            resolved.language = language
            resolved.sources["language"] = "current_request"
        elif preference := preferences.get("preferred_languages"):
            resolved.language = split_values(preference.value)[0]
            resolved.sources["language"] = "long_term_memory"

        if project.instruments:
            resolved.instruments = project.instruments
            resolved.sources["instruments"] = "project_control"
        elif requested_instruments := [
            instrument
            for instrument in ("钢琴", "原声吉他", "电吉他", "弦乐", "管弦乐", "合成器", "鼓组", "贝斯", "民族乐器")
            if instrument in project.user_request
        ]:
            resolved.instruments = requested_instruments
            resolved.sources["instruments"] = "current_request"
        elif preference := preferences.get("preferred_instruments"):
            resolved.instruments = split_values(preference.value)
            resolved.sources["instruments"] = "long_term_memory"

        if avoided := preferences.get("avoided_instruments"):
            avoided_values = set(split_values(avoided.value))
            resolved.instruments = [item for item in resolved.instruments if item not in avoided_values]

        if preference := preferences.get("default_duration"):
            resolved.default_duration = preference.value
            resolved.sources["default_duration"] = "long_term_memory"
        if preference := preferences.get("production_style"):
            resolved.production_style = preference.value
            resolved.sources["production_style"] = "long_term_memory"
        return resolved

    @staticmethod
    def portfolio_item(project: Project) -> PortfolioItem:
        completed = project.status == "completed"
        return PortfolioItem(
            project_id=project.id,
            title=project.title,
            user_request=project.user_request,
            preset=project.preset,
            status=project.status,
            progress=100 if completed and project.progress == 0 else project.progress,
            current_stage=(
                "completed"
                if completed and project.current_stage == "draft"
                else project.current_stage
            ),
            latest_run_id=project.latest_run_id,
            updated_at=project.updated_at,
        )
