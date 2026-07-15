from pathlib import Path
from threading import RLock
from uuid import uuid4

from fastapi.encoders import jsonable_encoder

from models.project import Asset, Project, ProjectCreate, RunResult, utc_now


class ProjectNotFoundError(FileNotFoundError):
    pass


class LocalProjectStore:
    def __init__(self, root: Path | str = "data/projects"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def list_projects(self) -> list[Project]:
        projects = [
            Project.model_validate_json(path.read_text(encoding="utf-8"))
            for path in self.root.glob("*/project.json")
        ]
        return sorted(projects, key=lambda project: project.updated_at, reverse=True)

    def create_project(self, data: ProjectCreate) -> Project:
        project = Project(**data.model_dump())
        self._project_dir(project.id).mkdir(parents=True)
        self.save_project(project)
        return project

    def get_project(self, project_id: str) -> Project:
        path = self._project_dir(project_id) / "project.json"
        if not path.is_file():
            raise ProjectNotFoundError(project_id)
        return Project.model_validate_json(path.read_text(encoding="utf-8"))

    def save_project(self, project: Project) -> None:
        with self._lock:
            project.updated_at = utc_now()
            directory = self._project_dir(project.id)
            directory.mkdir(parents=True, exist_ok=True)
            self._write_json(directory / "project.json", project)

    def add_asset(
        self,
        project_id: str,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> Asset:
        project = self.get_project(project_id)
        suffix = Path(filename).suffix.lower()
        asset = Asset(
            filename=Path(filename).name,
            path=f"assets/{uuid4().hex}{suffix}",
            content_type=content_type,
            size=len(content),
        )
        path = self._project_dir(project_id) / asset.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        project.assets.append(asset)
        self.save_project(project)
        return asset

    def save_run(self, project_id: str, state: dict) -> RunResult:
        project = self.get_project(project_id)
        run = RunResult(project_id=project_id, state=jsonable_encoder(state))
        self.save_run_result(run)
        project.latest_run_id = run.id
        project.status = "completed"
        project.progress = 100
        project.current_stage = "completed"
        project.workflow = state.get("workflow")
        project.error = None
        self.save_project(project)
        return run

    def create_run(self, project_id: str) -> RunResult:
        project = self.get_project(project_id)
        run = RunResult(
            project_id=project_id,
            status="running",
            progress=0,
            current_stage="queued",
        )
        self.save_run_result(run)
        project.latest_run_id = run.id
        project.status = "running"
        project.progress = 0
        project.current_stage = "queued"
        project.error = None
        self.save_project(project)
        return run

    def update_run(
        self,
        run: RunResult,
        *,
        progress: int,
        current_stage: str,
        status: str | None = None,
        state: dict | None = None,
        error: str | None = None,
    ) -> RunResult:
        run.progress = progress
        run.current_stage = current_stage
        if status is not None:
            run.status = status
        if state is not None:
            run.state = jsonable_encoder(state)
        run.error = error
        run.updated_at = utc_now()
        self.save_run_result(run)

        project = self.get_project(run.project_id)
        project.latest_run_id = run.id
        project.progress = progress
        project.current_stage = current_stage
        project.status = run.status
        project.error = error
        if state and state.get("workflow"):
            project.workflow = state["workflow"]
        self.save_project(project)
        return run

    def save_run_result(self, run: RunResult) -> None:
        path = self._project_dir(run.project_id) / "runs" / f"{run.id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            self._write_json(path, run)

    def get_run(self, project_id: str, run_id: str) -> RunResult:
        path = self._project_dir(project_id) / "runs" / f"{run_id}.json"
        if not path.is_file():
            raise ProjectNotFoundError(run_id)
        return RunResult.model_validate_json(path.read_text(encoding="utf-8"))

    def list_runs(self, project_id: str) -> list[RunResult]:
        self.get_project(project_id)
        runs = [
            RunResult.model_validate_json(path.read_text(encoding="utf-8"))
            for path in (self._project_dir(project_id) / "runs").glob("*.json")
        ]
        return sorted(runs, key=lambda run: run.created_at, reverse=True)

    def recover_interrupted_runs(self) -> int:
        recovered = 0
        for project in self.list_projects():
            if project.status != "running":
                continue
            reason = "Local worker stopped before the run completed"
            if project.latest_run_id:
                try:
                    run = self.get_run(project.id, project.latest_run_id)
                    self.update_run(
                        run,
                        progress=run.progress,
                        current_stage="interrupted",
                        status="failed",
                        error=reason,
                    )
                    recovered += 1
                    continue
                except ProjectNotFoundError:
                    pass
            project.status = "failed"
            project.current_stage = "interrupted"
            project.error = reason
            self.save_project(project)
            recovered += 1
        return recovered

    def artifact_dir(self, project_id: str) -> Path:
        self.get_project(project_id)
        path = self._project_dir(project_id) / "artifacts"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def asset_file_path(self, project_id: str, asset: Asset) -> Path:
        self.get_project(project_id)
        return self._project_dir(project_id) / asset.path

    def _project_dir(self, project_id: str) -> Path:
        if not project_id.isalnum():
            raise ProjectNotFoundError(project_id)
        return self.root / project_id

    @staticmethod
    def _write_json(path: Path, model: Project | RunResult) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(model.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(path)
