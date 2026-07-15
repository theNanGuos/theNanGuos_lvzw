import json
import time

from fastapi.testclient import TestClient

from app.api import create_app
from app.memory import LocalMemoryStore
from app.session_store import LocalSessionStore
from app.storage import LocalProjectStore
from providers.base import GeneratedTrack
from models.project import ProjectCreate
from tools.audio import AudioInspection, GeneratedAudioSummary, ToolExecutionError
from tools.demo_audio import DemoAudio


class FakeRunner:
    def __init__(self):
        self.inputs = []

    def invoke(self, state):
        self.inputs.append(state)
        return {
            **state,
            "workflow": "classical_instrumental",
            "final_prompt": "恢弘钢琴协奏曲，无人声。",
        }


class FakeMusicGenerator:
    def __init__(self):
        self.inputs = []

    def __call__(
        self,
        prompt,
        output_dir,
        *,
        instrumental=False,
        style=None,
        title=None,
        custom_mode=None,
    ):
        self.inputs.append(
            {
                "prompt": prompt,
                "output_dir": output_dir,
                "instrumental": instrumental,
                "style": style,
                "title": title,
                "custom_mode": custom_mode,
            }
        )
        path = output_dir / "generated.mp3"
        cover_path = output_dir / "generated.jpg"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"mp3 data")
        cover_path.write_bytes(b"cover data")
        return [
            GeneratedTrack(
                title=title or "generated",
                source_url="https://audio.test/generated.mp3",
                local_path=path,
                cover_source_url="https://image.test/generated.jpg",
                cover_path=cover_path,
                style="cinematic piano",
                duration_seconds=120,
            )
        ]


def fake_demo(prompt, output_path):
    output_path.write_bytes(b"demo")
    return DemoAudio(
        prompt=prompt,
        output_path=str(output_path),
        duration_seconds=12,
        tempo_bpm=96,
        frequencies=[220, 330, 440],
        size_bytes=4,
    )


def fake_summary(input_path, *, waveform_path=None):
    waveform_path.write_bytes(b"png")
    return GeneratedAudioSummary(
        inspection=AudioInspection(
            path=str(input_path),
            duration_seconds=123.4,
            codec_name="mp3",
            sample_rate=44100,
            size_bytes=8,
        ),
        waveform_path=str(waveform_path),
    )


def make_client(tmp_path):
    store = LocalProjectStore(tmp_path / "projects")
    runner = FakeRunner()
    generator = FakeMusicGenerator()
    app = create_app(
        store=store,
        session_store=LocalSessionStore(tmp_path / "sessions"),
        memory_store=LocalMemoryStore(tmp_path / "memory" / "user_profile.json"),
        runner_factory=lambda: runner,
        music_generator=generator,
        demo_renderer=fake_demo,
        audio_analyzer=fake_summary,
        works_root=tmp_path / "works",
    )
    return TestClient(app), store, runner, generator


class FakeChatAgent:
    def __init__(self):
        self.inputs = []

    def __call__(self, state):
        self.inputs.append(state)
        return {
            "reply": "我记住你偏好纯音乐，现在开始生成雨夜氛围电子曲。",
            "action": "run_workflow",
            "preset": "electronic_instrumental",
            "project_title": "雨夜电子",
            "user_request": "生成一首雨夜氛围电子纯音乐",
            "memory_observations": [
                {
                    "kind": "preference",
                    "key": "vocal_preference",
                    "value": "纯音乐",
                    "confidence": 0.95,
                    "evidence": "用户明确要求以后默认纯音乐",
                }
            ],
        }


def test_project_lifecycle_is_persisted_locally(tmp_path):
    client, store, runner, generator = make_client(tmp_path)

    response = client.post(
        "/api/projects",
        json={
            "title": "钢琴协奏曲",
            "user_request": "生成一首恢弘的钢琴协奏曲",
            "preset": "classical_instrumental",
        },
    )
    assert response.status_code == 201
    project = response.json()

    run_response = client.post(f"/api/projects/{project['id']}/runs")
    assert run_response.status_code == 200
    run = run_response.json()
    assert run["state"]["final_prompt"] == "恢弘钢琴协奏曲，无人声。"
    assert run["state"]["demo_audio"]["audio_url"].endswith("-demo.wav")
    assert run["state"]["generated_tracks"][0]["audio_url"] == "/works/generated.mp3"
    assert run["state"]["generated_tracks"][0]["cover_url"] == "/works/generated.jpg"
    assert run["state"]["generated_audio_analysis"][0]["waveform_url"] == "/works/generated-waveform.png"
    assert run["state"]["generated_audio_analysis"][0]["inspection"]["duration_seconds"] == 123.4
    assert generator.inputs[0]["output_dir"] == tmp_path / "works"
    assert generator.inputs[0]["custom_mode"] is True
    assert generator.inputs[0]["instrumental"] is True
    assert runner.inputs[0]["preset"] == "classical_instrumental"

    saved_project = json.loads(
        (store.root / project["id"] / "project.json").read_text(encoding="utf-8")
    )
    assert saved_project["status"] == "completed"
    assert saved_project["latest_run_id"] == run["id"]
    assert (store.root / project["id"] / "runs" / f"{run['id']}.json").is_file()

    audio_response = client.get(run["state"]["generated_tracks"][0]["audio_url"])
    assert audio_response.status_code == 200
    assert audio_response.content == b"mp3 data"


def test_audio_tool_failures_do_not_abort_music_generation(tmp_path):
    store = LocalProjectStore(tmp_path / "projects")
    runner = FakeRunner()
    generator = FakeMusicGenerator()
    app = create_app(
        store=store,
        session_store=LocalSessionStore(tmp_path / "sessions"),
        memory_store=LocalMemoryStore(tmp_path / "memory" / "user_profile.json"),
        runner_factory=lambda: runner,
        music_generator=generator,
        demo_renderer=lambda *args, **kwargs: (_ for _ in ()).throw(
            ToolExecutionError("ffmpeg missing")
        ),
        audio_analyzer=lambda *args, **kwargs: (_ for _ in ()).throw(
            ToolExecutionError("ffprobe missing")
        ),
        works_root=tmp_path / "works",
    )
    client = TestClient(app)
    project = client.post(
        "/api/projects",
        json={"title": "工具失败", "user_request": "生成一首歌"},
    ).json()

    run_response = client.post(f"/api/projects/{project['id']}/runs")

    assert run_response.status_code == 200
    state = run_response.json()["state"]
    assert state["generated_tracks"]
    assert state["demo_audio_error"] == "ffmpeg missing"
    assert state["generated_audio_analysis_error"] == "ffprobe missing"


def test_audio_upload_is_saved_as_project_asset(tmp_path):
    client, store, runner, _ = make_client(tmp_path)
    project = client.post(
        "/api/projects",
        json={"title": "参考音频", "user_request": "参考上传的音频创作"},
    ).json()

    response = client.post(
        f"/api/projects/{project['id']}/assets",
        files={"file": ("reference.mp3", b"fake audio", "audio/mpeg")},
    )

    assert response.status_code == 200
    asset = response.json()
    assert asset["filename"] == "reference.mp3"
    assert (store.root / project["id"] / asset["path"]).read_bytes() == b"fake audio"

    run_response = client.post(f"/api/projects/{project['id']}/runs")
    assert run_response.status_code == 200
    assert runner.inputs[0]["reference_audio_paths"] == [
        str(store.root / project["id"] / asset["path"])
    ]


def test_rejects_unsupported_asset_type(tmp_path):
    client, _, _, _ = make_client(tmp_path)
    project = client.post(
        "/api/projects",
        json={"title": "错误文件", "user_request": "测试"},
    ).json()

    response = client.post(
        f"/api/projects/{project['id']}/assets",
        files={"file": ("notes.txt", b"text", "text/plain")},
    )

    assert response.status_code == 400


def test_chat_session_routes_workflow_and_persists_memory(tmp_path):
    store = LocalProjectStore(tmp_path / "projects")
    sessions = LocalSessionStore(tmp_path / "sessions")
    memories = LocalMemoryStore(tmp_path / "memory" / "user_profile.json")
    runner = FakeRunner()
    chat_agent = FakeChatAgent()
    app = create_app(
        store=store,
        session_store=sessions,
        memory_store=memories,
        runner_factory=lambda: runner,
        chat_agent_factory=lambda: chat_agent,
        music_generator=FakeMusicGenerator(),
        demo_renderer=fake_demo,
        audio_analyzer=fake_summary,
        works_root=tmp_path / "works",
    )
    client = TestClient(app)
    session = client.post("/api/sessions", json={"title": "偏好测试"}).json()

    response = client.post(
        f"/api/sessions/{session['id']}/messages",
        json={"content": "以后默认做纯音乐，这次生成雨夜氛围电子曲"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "run_workflow"
    assert payload["project_id"]
    assert payload["run_id"]
    assert len(payload["session"]["messages"]) == 2
    assert memories.load_profile().preferences[0].value == "纯音乐"

    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        run = client.get(
            f"/api/projects/{payload['project_id']}/runs/{payload['run_id']}"
        ).json()
        if run["status"] != "running":
            break
        time.sleep(0.02)

    assert run["status"] == "completed"
    assert run["progress"] == 100
    assert runner.inputs[0]["memory_context"].preferences[0].value == "纯音乐"
    portfolio = client.get("/api/portfolio").json()
    assert portfolio[0]["project_id"] == payload["project_id"]
    assert portfolio[0]["status"] == "completed"
    assert portfolio[0]["tracks"][0]["cover_url"] == "/works/generated.jpg"
    assert portfolio[0]["tracks"][0]["duration_seconds"] == 123.4
    assert portfolio[0]["tracks"][0]["style"] == "cinematic piano"


def test_app_startup_marks_orphaned_local_run_as_interrupted(tmp_path):
    store = LocalProjectStore(tmp_path / "projects")
    project = store.create_project(
        ProjectCreate(title="未完成作品", user_request="生成一首测试音乐")
    )
    run = store.create_run(project.id)
    store.update_run(run, progress=42, current_stage="music_generation")

    create_app(
        store=store,
        session_store=LocalSessionStore(tmp_path / "sessions"),
        memory_store=LocalMemoryStore(tmp_path / "memory" / "user_profile.json"),
        runner_factory=lambda: FakeRunner(),
        music_generator=FakeMusicGenerator(),
        demo_renderer=fake_demo,
        audio_analyzer=fake_summary,
        works_root=tmp_path / "works",
    )

    recovered = store.get_run(project.id, run.id)
    assert recovered.status == "failed"
    assert recovered.progress == 42
    assert recovered.current_stage == "interrupted"
    assert store.get_project(project.id).status == "failed"
