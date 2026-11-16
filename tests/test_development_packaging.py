"""Keep the fork's app image distinct from the unchanged native integration."""

import json
import re
import tomllib
from pathlib import Path

from ha_growatt import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_development_package_and_app_versions_match():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert project["version"] == __version__
    app_version = __version__.replace(".dev", "-dev.")
    config = (ROOT / "addons/ha-growatt/config.yaml").read_text()
    assert f"version: {app_version}\n" in config
    assert "image: ghcr.io/loearthorbit/ha-growatt\n" in config
    assert "arch: [amd64, aarch64]\n" in config
    assert "slug: ha_growatt\n" in config
    wrapper = (ROOT / "addons/ha-growatt/Dockerfile").read_text()
    assert f"ARG BUILD_VERSION={app_version}\n" in wrapper
    assert "FROM ghcr.io/loearthorbit/ha-growatt:${BUILD_VERSION}\n" in wrapper
    assert 'CMD ["app"]' in wrapper


def test_image_targets_preserve_supervisor_and_standalone_entry_points():
    dockerfile = (ROOT / "Dockerfile").read_text()
    addon = dockerfile.split("FROM runtime AS addon\n", 1)[1]
    assert addon.startswith('USER 0:0\nCMD ["app"]\n')
    assert dockerfile.rstrip().endswith("FROM runtime AS standalone")
    runtime = dockerfile.split("FROM runtime AS addon\n", 1)[0]
    assert "USER 10001:10001\n" in runtime
    assert 'CMD ["container"]' in runtime
    assert "--require-hashes" in runtime
    assert "COPY src ./src" in runtime


def test_publication_waits_for_python_and_container_checks():
    workflow = (ROOT / ".github/workflows/development-image.yml").read_text()
    assert 'tags: ["v*-dev.*"]' in workflow
    assert 'python: ["3.12", "3.13", "3.14"]' in workflow
    for platform in ("linux/amd64", "linux/arm64", "linux/arm/v7"):
        assert f"platform: {platform}" in workflow
    assert "platform: linux/386" not in workflow
    assert "needs: [python, containers]" in workflow
    assert "github.repository == 'loearthorbit/HA-Growatt'" in workflow
    assert "container_probe.py --supervisor" in workflow
    assert '--target addon --build-arg VERSION="$IMAGE_VERSION"' in workflow
    assert "ghcr.io/loearthorbit/ha-growatt:$IMAGE_VERSION" in workflow
    assert re.search(r"uses: [^@\s]+@(?![a-f0-9]{40}\b)", workflow) is None


def test_native_integration_does_not_claim_to_install_the_development_receiver():
    manifest = json.loads((ROOT / "custom_components/ha_growatt/manifest.json").read_text())
    assert manifest["version"] == "0.9.0"
    assert manifest["requirements"] == [
        "ha-growatt@https://github.com/Herbertmt978/HA-Growatt/releases/download/"
        "v0.9.0/ha_growatt-0.9.0-py3-none-any.whl"
    ]
