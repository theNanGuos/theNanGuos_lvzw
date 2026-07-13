import json

from fastapi.testclient import TestClient

from app.api import create_app
from app.storage import LocalProjectStore


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


def make_client(tmp_path):
    store = LocalProjectStore(tmp_path / "projects")
    runner = FakeRunner()
    app = create_app(store=store, runner_factory=lambda: runner)
    return TestClient(app), store, runner


def test_project_lifecycle_is_persisted_locally(tmp_path):
    client, store, runner = make_client(tmp_path)

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
    assert runner.inputs[0]["preset"] == "classical_instrumental"

    saved_project = json.loads(
        (store.root / project["id"] / "project.json").read_text(encoding="utf-8")
    )
    assert saved_project["status"] == "completed"
    assert saved_project["latest_run_id"] == run["id"]
    assert (store.root / project["id"] / "runs" / f"{run['id']}.json").is_file()


def test_audio_upload_is_saved_as_project_asset(tmp_path):
    client, store, _ = make_client(tmp_path)
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
    client, _, _ = make_client(tmp_path)
    project = client.post(
        "/api/projects",
        json={"title": "错误文件", "user_request": "测试"},
    ).json()

    response = client.post(
        f"/api/projects/{project['id']}/assets",
        files={"file": ("notes.txt", b"text", "text/plain")},
    )

    assert response.status_code == 400
