import importlib.util
from pathlib import Path


SPEC = importlib.util.spec_from_file_location(
    "verify_macos_apps",
    Path(__file__).resolve().parents[1] / "scripts" / "verify_macos_apps.py",
)
verify_macos_apps = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(verify_macos_apps)


def test_verify_launchers_reports_ready_when_all_apps_exist(tmp_path):
    for app_name in verify_macos_apps.EXPECTED_APPS:
        contents = tmp_path / app_name / "Contents"
        contents.mkdir(parents=True)
        (contents / "Info.plist").write_text("<plist />", encoding="utf-8")

    result = verify_macos_apps.verify_launchers(tmp_path)

    assert result["status"] == "LAUNCHERS-READY"
    assert result["ready_count"] == len(verify_macos_apps.EXPECTED_APPS)
    assert result["missing"] == []


def test_verify_launchers_reports_missing_app(tmp_path):
    first = verify_macos_apps.EXPECTED_APPS[0]
    contents = tmp_path / first / "Contents"
    contents.mkdir(parents=True)
    (contents / "Info.plist").write_text("<plist />", encoding="utf-8")

    result = verify_macos_apps.verify_launchers(tmp_path)

    assert result["status"] == "LAUNCHERS-NO-GO"
    assert result["ready_count"] == 1
    assert verify_macos_apps.EXPECTED_APPS[1] in result["missing"]
