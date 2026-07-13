from pathlib import Path
from uuid import uuid4

from fastapi.encoders import jsonable_encoder

from models.project import Asset, Project, ProjectCreate, RunResult, utc_now


class ProjectNotFoundError(FileNotFoundError):
    pass


class LocalProjectStore:
    def __init__(self, root: Path | str = "data/projects"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

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
        path = self._project_dir(project_id) / "runs" / f"{run.id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        self._write_json(path, run)
        project.latest_run_id = run.id
        project.status = "completed"
        project.error = None
        self.save_project(project)
        return run

    def get_run(self, project_id: str, run_id: str) -> RunResult:
        path = self._project_dir(project_id) / "runs" / f"{run_id}.json"
        if not path.is_file():
            raise ProjectNotFoundError(run_id)
        return RunResult.model_validate_json(path.read_text(encoding="utf-8"))

    def artifact_dir(self, project_id: str) -> Path:
        self.get_project(project_id)
        path = self._project_dir(project_id) / "artifacts"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _project_dir(self, project_id: str) -> Path:
        if not project_id.isalnum():
            raise ProjectNotFoundError(project_id)
        return self.root / project_id

    @staticmethod
    def _write_json(path: Path, model: Project | RunResult) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(model.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(path)
