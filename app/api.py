from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from agents.init import create_llm
from app.graph import build_graph
from app.storage import LocalProjectStore, ProjectNotFoundError
from models.project import Asset, Project, ProjectCreate, RunResult

MAX_UPLOAD_SIZE = 20 * 1024 * 1024
ALLOWED_AUDIO_SUFFIXES = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}


class WorkflowRunner(Protocol):
    def invoke(self, state: dict) -> dict: ...


def create_app(
    store: LocalProjectStore | None = None,
    runner_factory: Callable[[], WorkflowRunner] | None = None,
) -> FastAPI:
    app = FastAPI(title="theNanGuos", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    project_store = store or LocalProjectStore()
    make_runner = runner_factory or (lambda: build_graph(create_llm()))
    runner: WorkflowRunner | None = None

    def get_project(project_id: str) -> Project:
        try:
            return project_store.get_project(project_id)
        except ProjectNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Project not found") from exc

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/projects", response_model=list[Project])
    def list_projects() -> list[Project]:
        return project_store.list_projects()

    @app.post("/api/projects", response_model=Project, status_code=status.HTTP_201_CREATED)
    def create_project(payload: ProjectCreate) -> Project:
        return project_store.create_project(payload)

    @app.get("/api/projects/{project_id}", response_model=Project)
    def read_project(project_id: str) -> Project:
        return get_project(project_id)

    @app.post("/api/projects/{project_id}/assets", response_model=Asset)
    async def upload_asset(
        project_id: str,
        file: UploadFile = File(...),
    ) -> Asset:
        get_project(project_id)
        filename = file.filename or "upload"
        if Path(filename).suffix.lower() not in ALLOWED_AUDIO_SUFFIXES:
            raise HTTPException(status_code=400, detail="Unsupported audio format")
        content = await file.read(MAX_UPLOAD_SIZE + 1)
        if len(content) > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail="Audio file exceeds 20 MB")
        return project_store.add_asset(
            project_id,
            filename,
            file.content_type or "application/octet-stream",
            content,
        )

    @app.post("/api/projects/{project_id}/runs", response_model=RunResult)
    def run_project(project_id: str) -> RunResult:
        nonlocal runner
        project = get_project(project_id)
        project.status = "running"
        project_store.save_project(project)
        try:
            runner = runner or make_runner()
            result = runner.invoke(
                {
                    "user_request": project.user_request,
                    "preset": project.preset,
                }
            )
            return project_store.save_run(project_id, result)
        except Exception as exc:
            project.status = "failed"
            project.error = str(exc)
            project_store.save_project(project)
            raise HTTPException(status_code=500, detail=f"Workflow failed: {exc}") from exc

    @app.get(
        "/api/projects/{project_id}/runs/{run_id}",
        response_model=RunResult,
    )
    def read_run(project_id: str, run_id: str) -> RunResult:
        get_project(project_id)
        try:
            return project_store.get_run(project_id, run_id)
        except ProjectNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Run not found") from exc

    return app


app = create_app()
