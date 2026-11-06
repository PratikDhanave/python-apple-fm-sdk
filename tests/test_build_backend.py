# For licensing see accompanying LICENSE file.
# Copyright (C) 2026 Apple Inc. All Rights Reserved.

"""Unit tests for Swift/SDK checks in build_backend.py."""

import subprocess
from types import SimpleNamespace

import pytest

import build_backend


def _completed(stdout: str = "", stderr: str = "", returncode: int = 0):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def test_build_succeeds_with_command_line_tools_only(monkeypatch, tmp_path):
    """Command Line Tools (Swift 6.2+, macOS 26 SDK) builds without xcodebuild."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "src" / "apple_fm_sdk").mkdir(parents=True)
    bin_dir = tmp_path / "fake_swift_bin"
    bin_dir.mkdir()
    (bin_dir / "libFoundationModels.dylib").write_bytes(b"")

    bindings_path = tmp_path / "src" / "apple_fm_sdk" / "_ctypes_bindings.py"

    monkeypatch.setattr(build_backend.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        build_backend.platform, "mac_ver", lambda: ("26.3", ("", "", ""), "")
    )
    monkeypatch.setattr(
        build_backend.shutil,
        "which",
        lambda cmd: "/usr/bin/swift" if cmd == "swift" else None,
    )

    executed_commands: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        executed_commands.append(list(cmd))
        if cmd[:2] == ["swift", "--version"]:
            return _completed(
                "Apple Swift version 6.2.3 (swiftlang-6.2.3.3.2 clang-1700.0.13.3)\n"
            )
        if cmd[:3] == ["xcrun", "--sdk", "macosx"]:
            return _completed("26.3\n")
        if cmd[:2] == ["swift", "build"] and "--show-bin-path" in cmd:
            return _completed(f"{bin_dir}\n")
        if cmd[:2] == ["swift", "build"]:
            return _completed("")
        if cmd[0] == "ctypesgen":
            bindings_path.write_text(
                "import ctypes\nimport sys\nadd_library_search_dirs(['lib'])\n"
            )
            return _completed("")
        raise AssertionError(f"Unexpected command invoked: {cmd}")

    monkeypatch.setattr(build_backend.subprocess, "run", fake_run)

    build_backend._build_c_bindings("release", None, None)

    # Ensure neither xcode-select nor xcodebuild was required
    binaries = [cmd[0] for cmd in executed_commands]
    assert "xcodebuild" not in binaries
    assert "xcode-select" not in binaries

    swift_build_cmd = next(
        cmd
        for cmd in executed_commands
        if cmd[:2] == ["swift", "build"] and "--show-bin-path" not in cmd
    )
    assert "-DFM_HAS_MACOS_27_SDK" not in swift_build_cmd
    assert "os.path.join(os.path.dirname(__file__), 'lib')" in bindings_path.read_text()


def test_build_passes_macos_27_sdk_flag_when_sdk_is_27_or_newer(monkeypatch, tmp_path):
    """macOS 27+ SDK enables -DFM_HAS_MACOS_27_SDK."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "src" / "apple_fm_sdk").mkdir(parents=True)
    bin_dir = tmp_path / "fake_swift_bin"
    bin_dir.mkdir()
    bindings_path = tmp_path / "src" / "apple_fm_sdk" / "_ctypes_bindings.py"

    monkeypatch.setattr(build_backend.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        build_backend.platform, "mac_ver", lambda: ("27.0.1", ("", "", ""), "")
    )
    monkeypatch.setattr(build_backend.shutil, "which", lambda cmd: "/usr/bin/swift")

    executed_commands: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        executed_commands.append(list(cmd))
        if cmd[:2] == ["swift", "--version"]:
            return _completed("Swift version 6.4.2 (swift-6.4.2-RELEASE)\n")
        if cmd[:3] == ["xcrun", "--sdk", "macosx"]:
            return _completed("27.2\n")
        if cmd[:2] == ["swift", "build"] and "--show-bin-path" in cmd:
            return _completed(f"{bin_dir}\n")
        if cmd[:2] == ["swift", "build"]:
            return _completed("")
        if cmd[0] == "ctypesgen":
            bindings_path.write_text("import sys\nadd_library_search_dirs(['lib'])\n")
            return _completed("")
        raise AssertionError(f"Unexpected command invoked: {cmd}")

    monkeypatch.setattr(build_backend.subprocess, "run", fake_run)

    build_backend._build_c_bindings("release", None, None)

    swift_build_cmd = next(
        cmd
        for cmd in executed_commands
        if cmd[:2] == ["swift", "build"] and "--show-bin-path" not in cmd
    )
    assert "-DFM_HAS_MACOS_27_SDK" in swift_build_cmd


def test_rejects_swift_older_than_6_2(monkeypatch):
    """Swift < 6.2 raises SwiftToolingError."""
    monkeypatch.setattr(build_backend.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        build_backend.platform, "mac_ver", lambda: ("26.0", ("", "", ""), "")
    )
    monkeypatch.setattr(build_backend.shutil, "which", lambda cmd: "/usr/bin/swift")
    monkeypatch.setattr(
        build_backend.subprocess,
        "run",
        lambda cmd, **kwargs: _completed("Apple Swift version 6.1.2\n"),
    )

    with pytest.raises(
        build_backend.SwiftToolingError,
        match=r"Swift version 6\.1 found, but version 6\.2 or higher is required",
    ):
        build_backend._build_c_bindings("release", None, None)


def test_rejects_macos_sdk_older_than_26(monkeypatch):
    """Active macOS SDK < 26 raises SwiftToolingError."""
    monkeypatch.setattr(build_backend.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        build_backend.platform, "mac_ver", lambda: ("26.3", ("", "", ""), "")
    )
    monkeypatch.setattr(build_backend.shutil, "which", lambda cmd: "/usr/bin/swift")

    def fake_run(cmd, **kwargs):
        if cmd[:2] == ["swift", "--version"]:
            return _completed("Apple Swift version 6.2.0\n")
        if cmd[:3] == ["xcrun", "--sdk", "macosx"]:
            return _completed("15.4\n")
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr(build_backend.subprocess, "run", fake_run)

    with pytest.raises(
        build_backend.SwiftToolingError,
        match="macOS SDK version 15 found, but version 26 or higher is required",
    ):
        build_backend._build_c_bindings("release", None, None)


def test_missing_sdk_or_license_error_message_has_proper_spacing(monkeypatch):
    """Error messages referencing Xcode license acceptance do not concatenate 'Xcodeat' (#16)."""
    monkeypatch.setattr(build_backend.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        build_backend.platform, "mac_ver", lambda: ("26.3", ("", "", ""), "")
    )
    monkeypatch.setattr(build_backend.shutil, "which", lambda cmd: "/usr/bin/swift")

    def fake_run_no_sdk(cmd, **kwargs):
        if cmd[:2] == ["swift", "--version"]:
            return _completed("Apple Swift version 6.2.3\n")
        raise subprocess.CalledProcessError(
            1, cmd, stderr="xcrun: error: unable to lookup item"
        )

    monkeypatch.setattr(build_backend.subprocess, "run", fake_run_no_sdk)

    with pytest.raises(build_backend.SwiftToolingError) as exc_info:
        build_backend._build_c_bindings("release", None, None)
    assert "Xcodeat" not in str(exc_info.value)
    assert "open Xcode at least once" in str(exc_info.value)

    def fake_run_license(cmd, **kwargs):
        raise subprocess.CalledProcessError(
            69,
            cmd,
            stderr="You have not agreed to the Xcode license agreements.",
        )

    monkeypatch.setattr(build_backend.subprocess, "run", fake_run_license)

    with pytest.raises(build_backend.SwiftToolingError) as exc_info_license:
        build_backend._build_c_bindings("release", None, None)
    assert "Xcodeat" not in str(exc_info_license.value)
    assert "open Xcode at least once" in str(exc_info_license.value)


def test_rejects_macos_older_than_26(monkeypatch):
    """macOS < 26.0 raises SwiftToolingError."""
    monkeypatch.setattr(build_backend.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        build_backend.platform, "mac_ver", lambda: ("15.5", ("", "", ""), "")
    )

    with pytest.raises(
        build_backend.SwiftToolingError,
        match="macOS version 15.5 found, but version 26.0 or higher is required",
    ):
        build_backend._build_c_bindings("release", None, None)


def test_rejects_missing_swift_executable(monkeypatch):
    """Missing swift executable in PATH raises SwiftToolingError."""
    monkeypatch.setattr(build_backend.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        build_backend.platform, "mac_ver", lambda: ("26.3", ("", "", ""), "")
    )
    monkeypatch.setattr(build_backend.shutil, "which", lambda cmd: None)

    with pytest.raises(
        build_backend.SwiftToolingError,
        match="No `swift` executable found in PATH",
    ):
        build_backend._build_c_bindings("release", None, None)
