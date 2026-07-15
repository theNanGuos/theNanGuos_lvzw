import json

from fastapi.testclient import TestClient

from app.api import create_app
from app.storage import LocalProjectStore
from providers.base import GeneratedTrack


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
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"mp3 data")
        return [
            GeneratedTrack(
                title=title or "generated",
                source_url="https://audio.test/generated.mp3",
                local_path=path,
            )
        ]


def make_client(tmp_path):
    store = LocalProjectStore(tmp_path / "projects")
    runner = FakeRunner()
    generator = FakeMusicGenerator()
    app = create_app(
        store=store,
        runner_factory=lambda: runner,
        music_generator=generator,
        works_root=tmp_path / "works",
    )
    return TestClient(app), store, runner, generator


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
    assert run["state"]["generated_tracks"][0]["audio_url"].endswith("/generated.mp3")
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


def test_audio_upload_is_saved_as_project_asset(tmp_path):
    client, store, _, _ = make_client(tmp_path)
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
