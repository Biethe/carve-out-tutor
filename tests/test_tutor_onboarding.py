"""Skipping the first questions saves a profile, but never wipes one that's already there."""
import os
import sys
import tempfile
from pathlib import Path

os.environ["TUTOR_DATA"] = tempfile.mkdtemp()  # before the tutor is imported: keep your real progress out of it
sys.path.insert(0, str(Path(__file__).parent.parent))
from fastapi.testclient import TestClient  # noqa: E402
from tutor import progress  # noqa: E402
from tutor.app import app  # noqa: E402

client = TestClient(app)


def test_skipping_never_wipes_a_finished_profile(monkeypatch, tmp_path):
    monkeypatch.setattr(progress, "DATA", tmp_path)
    monkeypatch.setattr(progress, "PROFILE", tmp_path / "profile.json")
    assert client.post("/api/onboarding", json={"answers": []}).json()["summary"] == "Skipped the first questions."
    client.post("/api/onboarding", json={"answers": [["python", True], ["web_hard", True], ["data_hard", True]]})
    assert "error" in client.post("/api/onboarding", json={"answers": []}).json()
    assert progress.load_profile()["level"] == "advanced"
