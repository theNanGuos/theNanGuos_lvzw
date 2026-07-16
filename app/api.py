from collections.abc import Callable
from pathlib import Path
from threading import Lock, Thread
from typing import Protocol

from fastapi import FastAPI, File, HTTPException, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from agents.chat import ChatAgent
from agents.init import create_llm
from app.graph import build_graph
from app.memory import (
    LocalMemoryStore,
    MemoryNotFoundError,
    canonical_key,
    extract_explicit_preferences,
    normalized_value,
)
from app.session_store import LocalSessionStore, SessionNotFoundError
from app.storage import LocalProjectStore, ProjectNotFoundError
from lib.logging_config import get_logger, log_context, setup_logging
from models.chat import (
    ChatAudioAttachment,
    ChatDecision,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatSession,
    ChatSessionCreate,
    ChatSessionSummary,
    ChatSessionUpdate,
    ChatWorkflowRun,
)
from models.memory import (
    EffectiveCreativePreferences,
    MemoryContext,
    PortfolioItem,
    PortfolioTrack,
    PreferenceUpdate,
    UserPreference,
    UserProfile,
)
from models.project import Asset, Project, ProjectCreate, RunResult
from providers.base import GeneratedTrack
from tools.audio import ToolExecutionError, summarize_generated_audio
from tools.demo_audio import render_prompt_demo_audio

MAX_UPLOAD_SIZE = 20 * 1024 * 1024
ALLOWED_AUDIO_SUFFIXES = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}
logger = get_logger(__name__)


class WorkflowRunner(Protocol):
    def invoke(self, state: dict) -> dict: ...


class ChatRunner(Protocol):
    def __call__(self, state: dict) -> dict: ...


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
        "instrumental": not bool(value_from(brief, "vocal", False)),
        "style": ", ".join(str(part) for part in style_parts if part),
        "title": str(value_from(brief, "title", project.title) or project.title),
        "custom_mode": True,
    }


def workflow_request(
    project: Project,
    resolved: EffectiveCreativePreferences,
) -> str:
    parameters = []
    if resolved.genre:
        parameters.append(f"流派：{resolved.genre}")
    if resolved.vocal is not None:
        parameters.append("人声：人声歌曲" if resolved.vocal else "人声：纯音乐")
    if resolved.language and resolved.vocal is not False:
        parameters.append(f"语言：{resolved.language}")
    if resolved.instruments:
        parameters.append(f"主要乐器：{'、'.join(resolved.instruments)}")
    if resolved.default_duration:
        parameters.append(f"默认时长：{resolved.default_duration}")
    if resolved.production_style:
        parameters.append(f"制作风格：{resolved.production_style}")
    if not parameters:
        return project.user_request
    return f"{project.user_request}\n\n创作参数：{'；'.join(parameters)}"


def generated_track_payload(track: GeneratedTrack, works_root: Path) -> dict[str, object]:
    path = track.local_path
    try:
        relative_path = path.resolve().relative_to(works_root.resolve())
    except ValueError:
        relative_path = Path(path.name)
    url_path = "/works/" + "/".join(relative_path.parts)
    cover_url = (
        relative_works_url(track.cover_path, works_root)
        if track.cover_path is not None
        else None
    )
    return {
        "title": track.title,
        "source_url": track.source_url,
        "local_path": str(path),
        "audio_url": url_path,
        "download_url": url_path,
        "cover_source_url": track.cover_source_url,
        "cover_path": str(track.cover_path) if track.cover_path else None,
        "cover_url": cover_url,
        "style": track.style,
        "duration_seconds": track.duration_seconds,
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
    session_store: LocalSessionStore | None = None,
    memory_store: LocalMemoryStore | None = None,
    runner_factory: Callable[[], WorkflowRunner] | None = None,
    chat_agent_factory: Callable[[], ChatRunner] | None = None,
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
    sessions = session_store or LocalSessionStore()
    memories = memory_store or LocalMemoryStore()
    interrupted_runs = project_store.recover_interrupted_runs()
    if interrupted_runs:
        logger.warning("interrupted_runs_recovered count=%s", interrupted_runs)
    works_directory = Path(works_root)
    works_directory.mkdir(parents=True, exist_ok=True)
    app.mount("/works", StaticFiles(directory=works_directory), name="works")
    make_runner = runner_factory or (lambda: build_graph(create_llm()))
    make_chat_agent = chat_agent_factory or (lambda: ChatAgent(create_llm()))
    if music_generator is None:
        from lib.suno import generate as music_generator
    runner: WorkflowRunner | None = None
    chat_agent: ChatRunner | None = None
    agent_lock = Lock()
    workflow_lock = Lock()

    def get_project(project_id: str) -> Project:
        try:
            return project_store.get_project(project_id)
        except ProjectNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Project not found") from exc

    def get_session(session_id: str) -> ChatSession:
        try:
            return sessions.get_session(session_id)
        except SessionNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Session not found") from exc

    def memory_context() -> MemoryContext:
        context = memories.context(project_store.list_projects())
        context.previous_works = [
            build_portfolio_item(project)
            for project in project_store.list_projects()[:20]
        ]
        return context

    def build_portfolio_item(project: Project) -> PortfolioItem:
        item = memories.portfolio_item(project)
        if not project.latest_run_id:
            return item
        try:
            run = project_store.get_run(project.id, project.latest_run_id)
        except ProjectNotFoundError:
            return item
        tracks = run.state.get("generated_tracks") or []
        analyses = run.state.get("generated_audio_analysis") or []
        brief = run.state.get("creative_brief") or {}
        fallback_style = value_from(brief, "genre", "") or value_from(
            brief,
            "production_style",
            "",
        )
        for index, track in enumerate(tracks):
            if not isinstance(track, dict) or not track.get("audio_url"):
                continue
            inspection = {}
            if index < len(analyses) and isinstance(analyses[index], dict):
                inspection = analyses[index].get("inspection") or {}
            duration = inspection.get("duration_seconds") or track.get("duration_seconds")
            item.tracks.append(
                PortfolioTrack(
                    title=str(track.get("title") or project.title),
                    audio_url=str(track["audio_url"]),
                    download_url=str(track.get("download_url") or track["audio_url"]),
                    cover_url=track.get("cover_url"),
                    duration_seconds=duration,
                    style=str(track.get("style") or fallback_style or ""),
                )
            )
        return item

    def get_workflow_runner() -> WorkflowRunner:
        nonlocal runner
        with agent_lock:
            runner = runner or make_runner()
        return runner

    def get_chat_runner() -> ChatRunner:
        nonlocal chat_agent
        with agent_lock:
            chat_agent = chat_agent or make_chat_agent()
        return chat_agent

    def update_progress(
        project_id: str,
        run: RunResult | None,
        progress: int,
        stage: str,
    ) -> None:
        if run is not None:
            project_store.update_run(
                run,
                progress=progress,
                current_stage=stage,
                status="running",
            )
            return
        project = project_store.get_project(project_id)
        project.status = "running"
        project.progress = progress
        project.current_stage = stage
        project.error = None
        project_store.save_project(project)

    def execute_workflow(project_id: str, run: RunResult | None = None) -> RunResult:
        project = project_store.get_project(project_id)
        with workflow_lock, log_context(project_id=project_id, stage="workflow"):
            logger.info("workflow_started preset=%s run_id=%s", project.preset, run.id if run else "sync")
            try:
                update_progress(project_id, run, 10, "workflow")
                effective_preferences = memories.resolve_preferences(project)
                result = get_workflow_runner().invoke(
                    {
                        "project_id": project_id,
                        "user_request": workflow_request(project, effective_preferences),
                        "preset": project.preset,
                        "memory_context": memory_context(),
                        "effective_preferences": effective_preferences,
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

                update_progress(project_id, run, 75, "demo_audio")
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

                update_progress(project_id, run, 82, "music_generation")
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

                update_progress(project_id, run, 95, "audio_analysis")
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

                if run is None:
                    completed = project_store.save_run(project_id, result)
                else:
                    completed = project_store.update_run(
                        run,
                        progress=100,
                        current_stage="completed",
                        status="completed",
                        state=result,
                    )
                memories.record_workflow(str(result.get("workflow") or project.preset))
                with log_context(project_id=project_id, run_id=completed.id, stage="workflow"):
                    logger.info("workflow_completed tracks=%s", len(result["generated_tracks"]))
                return completed
            except Exception as exc:
                if run is not None:
                    project_store.update_run(
                        run,
                        progress=run.progress,
                        current_stage="failed",
                        status="failed",
                        error=str(exc),
                    )
                else:
                    failed_project = project_store.get_project(project_id)
                    failed_project.status = "failed"
                    failed_project.current_stage = "failed"
                    failed_project.error = str(exc)
                    project_store.save_project(failed_project)
                logger.exception("workflow_failed")
                raise

    def execute_workflow_in_background(project_id: str, run: RunResult) -> None:
        try:
            execute_workflow(project_id, run)
        except Exception:
            # execute_workflow persists and logs the actionable error.
            return

    def start_background_run(project_id: str) -> RunResult:
        run = project_store.create_run(project_id)
        Thread(
            target=execute_workflow_in_background,
            args=(project_id, run),
            daemon=True,
            name=f"music-run-{run.id[:8]}",
        ).start()
        return run

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/projects", response_model=list[Project])
    def list_projects() -> list[Project]:
        return project_store.list_projects()

    @app.get("/api/portfolio", response_model=list[PortfolioItem])
    def list_portfolio() -> list[PortfolioItem]:
        return memory_context().previous_works

    @app.get("/api/memory", response_model=UserProfile)
    def read_memory() -> UserProfile:
        return memories.load_profile()

    @app.patch("/api/memory/preferences/{key}", response_model=UserPreference)
    def update_memory_preference(key: str, payload: PreferenceUpdate) -> UserPreference:
        try:
            preference = memories.update_preference(key, payload)
        except MemoryNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Memory preference not found") from exc
        logger.info("memory_preference_updated key=%s", preference.key)
        return preference

    @app.delete("/api/memory/preferences/{key}", response_model=UserProfile)
    def delete_memory_preference(key: str) -> UserProfile:
        try:
            profile = memories.delete_preference(key)
        except MemoryNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Memory preference not found") from exc
        logger.info("memory_preference_deleted key=%s", key)
        return profile

    @app.delete("/api/memory", response_model=UserProfile)
    def clear_memory() -> UserProfile:
        logger.info("memory_cleared")
        return memories.clear()

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
        get_project(project_id)
        try:
            return execute_workflow(project_id)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Workflow failed: {exc}") from exc

    @app.post("/api/projects/{project_id}/runs/async", response_model=RunResult)
    def run_project_async(project_id: str) -> RunResult:
        get_project(project_id)
        run = start_background_run(project_id)
        logger.info("workflow_queued project_id=%s run_id=%s", project_id, run.id)
        return run

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

    @app.get("/api/sessions", response_model=list[ChatSessionSummary])
    def list_sessions() -> list[ChatSessionSummary]:
        return [
            ChatSessionSummary(
                id=session.id,
                title=session.title,
                active_project_id=session.active_project_id,
                message_count=len(session.messages),
                created_at=session.created_at,
                updated_at=session.updated_at,
            )
            for session in sessions.list_sessions()
        ]

    @app.post("/api/sessions", response_model=ChatSession, status_code=status.HTTP_201_CREATED)
    def create_session(payload: ChatSessionCreate) -> ChatSession:
        session = sessions.create_session(payload)
        logger.info("chat_session_created session_id=%s", session.id)
        return session

    @app.post(
        "/api/sessions/{session_id}/assets",
        response_model=ChatAudioAttachment,
        status_code=status.HTTP_201_CREATED,
    )
    async def upload_session_asset(
        session_id: str,
        file: UploadFile = File(...),
    ) -> ChatAudioAttachment:
        get_session(session_id)
        filename = file.filename or "reference-audio"
        if Path(filename).suffix.lower() not in ALLOWED_AUDIO_SUFFIXES:
            raise HTTPException(status_code=400, detail="Unsupported audio format")
        content = await file.read(MAX_UPLOAD_SIZE + 1)
        if len(content) > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail="Audio file exceeds 20 MB")
        asset = sessions.add_asset(
            session_id,
            filename,
            file.content_type or "application/octet-stream",
            content,
        )
        with log_context(stage="chat_asset_upload"):
            logger.info(
                "chat_asset_uploaded session_id=%s filename=%s size=%s",
                session_id,
                asset.filename,
                asset.size,
            )
        return asset

    @app.get("/api/sessions/{session_id}", response_model=ChatSession)
    def read_session(session_id: str) -> ChatSession:
        return get_session(session_id)

    @app.patch("/api/sessions/{session_id}", response_model=ChatSession)
    def update_session(session_id: str, payload: ChatSessionUpdate) -> ChatSession:
        get_session(session_id)
        session = sessions.update_session(session_id, payload)
        logger.info("chat_session_updated session_id=%s", session_id)
        return session

    @app.delete("/api/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_session(session_id: str) -> Response:
        get_session(session_id)
        sessions.delete_session(session_id)
        logger.info("chat_session_deleted session_id=%s", session_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post("/api/sessions/{session_id}/messages", response_model=ChatResponse)
    def send_message(session_id: str, payload: ChatRequest) -> ChatResponse:
        session = get_session(session_id)
        assets_by_id = {asset.id: asset for asset in session.assets}
        try:
            attached_assets = [assets_by_id[asset_id] for asset_id in payload.asset_ids]
        except KeyError as exc:
            raise HTTPException(status_code=400, detail="Chat audio attachment not found") from exc
        user_message = ChatMessage(
            role="user",
            content=payload.content,
            audio_attachments=attached_assets,
        )
        session.messages.append(user_message)
        if len(session.messages) > 20:
            older_messages = session.messages[:-20]
            session.summary = "\n".join(
                f"{message.role}: {message.content}" for message in older_messages
            )[-4000:]
        sessions.save_session(session)

        context = memory_context()
        try:
            raw_decision = get_chat_runner()(
                {
                    "latest_message": payload.content,
                    "recent_messages": [
                        message.model_dump(mode="json") for message in session.messages[-20:]
                    ],
                    "session_summary": session.summary,
                    "active_project_id": session.active_project_id,
                    "memory_context": context,
                    "reference_audio_attachments": [
                        {
                            "filename": asset.filename,
                            "content_type": asset.content_type,
                            "size": asset.size,
                        }
                        for asset in attached_assets
                    ],
                }
            )
            decision = ChatDecision.model_validate(raw_decision)
        except Exception as exc:
            logger.exception("chat_agent_failed session_id=%s", session_id)
            raise HTTPException(status_code=500, detail=f"南郭先生响应失败: {exc}") from exc

        normalized_observations = {}
        candidates = [
            *decision.memory_observations,
            *extract_explicit_preferences(payload.content),
        ]
        for observation in candidates:
            key = canonical_key(observation.key)
            if key is None:
                continue
            normalized_observations[key] = observation.model_copy(
                update={"key": key, "value": normalized_value(key, observation.value)}
            )
        remembered_preferences = list(normalized_observations.values())
        if remembered_preferences:
            memories.merge_observations(
                remembered_preferences,
                session_id=session_id,
            )
            logger.info(
                "memory_observations_merged session_id=%s count=%s",
                session_id,
                len(remembered_preferences),
            )

        project_id: str | None = None
        run_id: str | None = None
        if decision.action in {"create_project", "run_workflow", "revise_project"}:
            request_text = decision.user_request.strip() or payload.content
            title = decision.project_title.strip() or request_text[:40]
            if decision.action == "revise_project" and session.active_project_id:
                project = get_project(session.active_project_id)
                project.title = title
                project.user_request = request_text
                project.preset = decision.preset
                project.status = "draft"
                project.progress = 0
                project.current_stage = "draft"
                project_store.save_project(project)
            else:
                project = project_store.create_project(
                    ProjectCreate(
                        title=title,
                        user_request=request_text,
                        preset=decision.preset,
                    )
                )
            project_id = project.id
            session.active_project_id = project.id
            for asset in attached_assets:
                project_store.add_asset(
                    project.id,
                    asset.filename,
                    asset.content_type,
                    sessions.asset_file_path(session_id, asset).read_bytes(),
                )
            if decision.action in {"run_workflow", "revise_project"}:
                run_id = start_background_run(project.id).id

        workflow_run = None
        if project_id and run_id:
            workflow_run = ChatWorkflowRun(
                project_id=project_id,
                run_id=run_id,
                title=project.title,
                preset=project.preset,
            )
        assistant_message = ChatMessage(
            role="assistant",
            content=decision.reply,
            workflow_run=workflow_run,
            remembered_preferences=remembered_preferences,
        )
        session.messages.append(assistant_message)
        sessions.save_session(session)
        logger.info(
            "chat_message_completed session_id=%s action=%s project_id=%s run_id=%s",
            session_id,
            decision.action,
            project_id,
            run_id,
        )
        return ChatResponse(
            session=session,
            message=assistant_message,
            action=decision.action,
            project_id=project_id,
            run_id=run_id,
            remembered_preferences=remembered_preferences,
        )

    return app


app = create_app()
