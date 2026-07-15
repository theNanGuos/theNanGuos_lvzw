from pathlib import Path
from threading import RLock

from models.memory import (
    MemoryContext,
    MemoryObservation,
    PortfolioItem,
    UserPreference,
    UserProfile,
)
from models.project import Project, utc_now


class LocalMemoryStore:
    def __init__(self, path: Path | str = "data/memory/user_profile.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def load_profile(self) -> UserProfile:
        if not self.path.is_file():
            return UserProfile()
        return UserProfile.model_validate_json(self.path.read_text(encoding="utf-8"))

    def merge_observations(
        self,
        observations: list[MemoryObservation],
        *,
        session_id: str,
    ) -> UserProfile:
        with self._lock:
            profile = self.load_profile()
            for observation in observations:
                existing = next(
                    (
                        preference
                        for preference in profile.preferences
                        if preference.kind == observation.kind
                        and preference.key == observation.key
                        and preference.value == observation.value
                    ),
                    None,
                )
                if existing is None:
                    profile.preferences.append(
                        UserPreference(
                            **observation.model_dump(exclude={"evidence"}),
                            source_session_ids=[session_id],
                        )
                    )
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

    @staticmethod
    def portfolio_item(project: Project) -> PortfolioItem:
        return PortfolioItem(
            project_id=project.id,
            title=project.title,
            user_request=project.user_request,
            preset=project.preset,
            status=project.status,
            progress=project.progress,
            current_stage=project.current_stage,
            latest_run_id=project.latest_run_id,
            updated_at=project.updated_at,
        )
