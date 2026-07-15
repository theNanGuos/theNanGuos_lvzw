from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from agents.init import create_llm
from app.graph import build_graph
from app.storage import LocalProjectStore, ProjectNotFoundError
from lib.logging_config import get_logger, log_context, setup_logging
from models.project import Asset, Project, ProjectCreate, RunResult
from providers.base import GeneratedTrack
from tools.audio import ToolExecutionError, summarize_generated_audio
from tools.demo_audio import render_prompt_demo_audio

MAX_UPLOAD_SIZE = 20 * 1024 * 1024
ALLOWED_AUDIO_SUFFIXES = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}
logger = get_logger(__name__)


class WorkflowRunner(Protocol):
    def invoke(self, state: dict) -> dict: ...


class MusicGenerator(Protocol):
    def __call__(
        self,
        prompt: str,
        output_dir: Path | str,
        *,
        instrumental: bool = False,
        style: str | None = None,
        title: str | None = None,
        custom_mode: bool | None = None,
    ) -> list[GeneratedTrack]: ...


class DemoRenderer(Protocol):
    def __call__(self, prompt: str, output_path: Path | str): ...


class AudioAnalyzer(Protocol):
    def __call__(
        self,
        input_path: Path | str,
        *,
        waveform_path: Path | str | None = None,
    ): ...


def value_from(data: object, field: str, default: object = None) -> object:
    if isinstance(data, dict):
        return data.get(field, default)
    return getattr(data, field, default)


def generation_options(state: dict, project: Project) -> dict[str, object]:
    brief = state.get("creative_brief")
    style_parts = [
        value_from(brief, "genre", ""),
        value_from(brief, "production_style", ""),
    ]
    style_parts.extend(value_from(brief, "mood", []) or [])
    return {
        "instrumental": state.get("workflow") == "classical_instrumental",
        "style": ", ".join(str(part) for part in style_parts if part),
        "title": str(value_from(brief, "title", project.title) or project.title),
        "custom_mode": True,
    }


def generated_track_payload(track: GeneratedTrack, works_root: Path) -> dict[str, str]:
    path = track.local_path
    try:
        relative_path = path.resolve().relative_to(works_root.resolve())
    except ValueError:
        relative_path = Path(path.name)
    url_path = "/works/" + "/".join(relative_path.parts)
    return {
        "title": track.title,
        "source_url": track.source_url,
        "local_path": str(path),
        "audio_url": url_path,
        "download_url": url_path,
    }


def relative_works_url(path: Path, works_root: Path) -> str:
    try:
        relative_path = path.resolve().relative_to(works_root.resolve())
    except ValueError:
        relative_path = Path(path.name)
    return "/works/" + "/".join(relative_path.parts)


def build_prompt_demo_audio(
    prompt: str,
    project_id: str,
    works_root: Path,
    demo_renderer: DemoRenderer,
) -> dict[str, object]:
    output_path = works_root / f"{project_id}-demo.wav"
    demo = demo_renderer(prompt, output_path)
    payload = demo.model_dump(mode="json")
    payload["audio_url"] = relative_works_url(output_path, works_root)
    return payload


def analyze_generated_tracks(
    tracks: list[GeneratedTrack],
    works_root: Path,
    audio_analyzer: AudioAnalyzer,
) -> list[dict[str, object]]:
    analyses = []
    for track in tracks:
        waveform_path = works_root / f"{Path(track.local_path).stem}-waveform.png"
        summary = audio_analyzer(track.local_path, waveform_path=waveform_path)
        payload = summary.model_dump(mode="json")
        payload["track_title"] = track.title
        if summary.waveform_path:
            payload["waveform_url"] = relative_works_url(Path(summary.waveform_path), works_root)
        analyses.append(payload)
    return analyses


def create_app(
    store: LocalProjectStore | None = None,
    runner_factory: Callable[[], WorkflowRunner] | None = None,
    music_generator: MusicGenerator | None = None,
    demo_renderer: DemoRenderer = render_prompt_demo_audio,
    audio_analyzer: AudioAnalyzer = summarize_generated_audio,
    works_root: Path | str = "works",
) -> FastAPI:
    setup_logging("api")
    app = FastAPI(title="theNanGuos", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    project_store = store or LocalProjectStore()
    works_directory = Path(works_root)
    works_directory.mkdir(parents=True, exist_ok=True)
    app.mount("/works", StaticFiles(directory=works_directory), name="works")
    make_runner = runner_factory or (lambda: build_graph(create_llm()))
    if music_generator is None:
        from lib.suno import generate as music_generator
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
        project = project_store.create_project(payload)
        logger.info("project_created title=%s preset=%s", project.title, project.preset)
        return project

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
        asset = project_store.add_asset(
            project_id,
            filename,
            file.content_type or "application/octet-stream",
            content,
        )
        with log_context(project_id=project_id, stage="asset_upload"):
            logger.info(
                "asset_uploaded filename=%s content_type=%s size=%s",
                asset.filename,
                asset.content_type,
                asset.size,
            )
        return asset

    @app.post("/api/projects/{project_id}/runs", response_model=RunResult)
    def run_project(project_id: str) -> RunResult:
        nonlocal runner
        project = get_project(project_id)
        project.status = "running"
        project_store.save_project(project)
        with log_context(project_id=project_id, stage="workflow"):
            logger.info("workflow_started preset=%s", project.preset)
            try:
                runner = runner or make_runner()
                result = runner.invoke(
                    {
                        "user_request": project.user_request,
                        "preset": project.preset,
                        "artifact_dir": str(project_store.artifact_dir(project_id)),
                        "reference_audio_paths": [
                            str(project_store.asset_file_path(project_id, asset))
                            for asset in project.assets
                        ],
                    }
                )
                final_prompt = result.get("final_prompt")
                if not isinstance(final_prompt, str) or not final_prompt:
                    raise RuntimeError("Workflow completed without final_prompt")
                with log_context(project_id=project_id, stage="demo_audio"):
                    try:
                        result["demo_audio"] = build_prompt_demo_audio(
                            final_prompt,
                            project_id,
                            works_directory,
                            demo_renderer,
                        )
                        logger.info("demo_audio_created")
                    except ToolExecutionError as exc:
                        result["demo_audio_error"] = str(exc)
                        logger.warning("demo_audio_failed reason=%s", exc)
                with log_context(project_id=project_id, stage="music_generation"):
                    options = generation_options(result, project)
                    logger.info(
                        "music_generation_requested instrumental=%s custom_mode=%s",
                        options["instrumental"],
                        options["custom_mode"],
                    )
                    tracks = music_generator(
                        final_prompt,
                        works_directory,
                        instrumental=bool(options["instrumental"]),
                        style=str(options["style"] or ""),
                        title=str(options["title"] or project.title),
                        custom_mode=bool(options["custom_mode"]),
                    )
                result["generated_tracks"] = [
                    generated_track_payload(track, works_directory)
                    for track in tracks
                ]
                with log_context(project_id=project_id, stage="generated_audio_analysis"):
                    try:
                        result["generated_audio_analysis"] = analyze_generated_tracks(
                            tracks,
                            works_directory,
                            audio_analyzer,
                        )
                        logger.info(
                            "generated_audio_analysis_completed tracks=%s",
                            len(result["generated_audio_analysis"]),
                        )
                    except ToolExecutionError as exc:
                        result["generated_audio_analysis_error"] = str(exc)
                        logger.warning("generated_audio_analysis_failed reason=%s", exc)
                run = project_store.save_run(project_id, result)
                with log_context(project_id=project_id, run_id=run.id, stage="workflow"):
                    logger.info("workflow_completed tracks=%s", len(result["generated_tracks"]))
                return run
            except Exception as exc:
                project.status = "failed"
                project.error = str(exc)
                project_store.save_project(project)
                logger.exception("workflow_failed")
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
