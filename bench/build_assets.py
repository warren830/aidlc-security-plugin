#!/usr/bin/env python3
"""Build the asset dir that every arm's container setup reads as $BENCH_ASSETS.

    python bench/build_assets.py --out DIR [--work DIR] [--config FILE]

It holds the security plugin's Claude projection built from PLUGIN_COMMIT
with the aidlc-workflows tools at AIDLC_WORKFLOWS_BUILD_COMMIT, the AI-DLC
release files for an offline install, pinned bun and uv binaries, the pins
the setup scripts read (pins.env), and manifest.json with every commit and
checksum. Downloads and checkouts are cached in --work, so a rerun only
rebuilds the asset dir, which replaces the old one in one rename.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pins as pinfile

MARKETPLACE_DIR = "security-plugin"
RELEASE_DIR = "aidlc-release"
CONTAINER_PINS = ("AIDLC_VERSION", "SECURITY_AGENT_MCP", "SECURITY_AGENT_REGION")


@dataclass(frozen=True)
class Arch:
    aidlc: str
    bun: str
    uv: str


ARCHES = {
    "x86_64": Arch("x64", "bun-linux-x64-baseline", "x86_64-unknown-linux-musl"),
    "aarch64": Arch("arm64", "bun-linux-aarch64", "aarch64-unknown-linux-musl"),
}
ARCH_ALIASES = {"amd64": "x86_64", "arm64": "aarch64"}


def host_arch() -> Arch:
    machine = platform.machine().lower()
    return ARCHES[ARCH_ALIASES.get(machine, machine)]


def run(command: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    print(f"build-assets: {' '.join(command)}", file=sys.stderr, flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, dest: Path) -> Path:
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        partial = dest.with_name(dest.name + ".partial")
        print(f"build-assets: download {url}", file=sys.stderr, flush=True)
        urllib.request.urlretrieve(url, partial)
        partial.rename(dest)
    return dest


def checked(path: Path, expected: str) -> str:
    actual = sha256(path)
    if actual != expected:
        path.unlink()
        raise SystemExit(f"build-assets: {path.name} has sha256 {actual}, expected {expected}")
    return actual


def listed_sums(path: Path) -> dict[str, str]:
    """name -> sha256 from a `sha256sum`-style file."""
    sums = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2:
            sums[parts[1].lstrip("*")] = parts[0]
    return sums


def aidlc_release(pins: dict[str, str], arch: Arch, downloads: Path) -> dict[str, str]:
    version = pins["AIDLC_VERSION"]
    base = f"{pins['AIDLC_RELEASE_URL']}/v{version}"
    folder = downloads / f"aidlc-{version}-{arch.aidlc}"
    sums = listed_sums(download(f"{base}/checksums.txt", folder / "checksums.txt"))
    files = ["install.sh", "version.json", f"aidlc-runtime-{version}.tar.gz", f"aidlc-linux-{arch.aidlc}"]
    checksums = {name: checked(download(f"{base}/{name}", folder / name), sums[name]) for name in files}
    download(f"{base}/aidlc-release.intoto.jsonl", folder / "aidlc-release.intoto.jsonl")
    return checksums


def bun(pins: dict[str, str], arch: Arch, downloads: Path) -> tuple[Path, str]:
    base = f"https://github.com/oven-sh/bun/releases/download/bun-v{pins['BUN_VERSION']}"
    folder = downloads / f"bun-{pins['BUN_VERSION']}"
    archive = download(f"{base}/{arch.bun}.zip", folder / f"{arch.bun}.zip")
    digest = checked(archive, listed_sums(download(f"{base}/SHASUMS256.txt", folder / "SHASUMS256.txt"))[archive.name])
    binary = folder / arch.bun / "bun"
    if not binary.exists():
        with zipfile.ZipFile(archive) as bundle:
            bundle.extract(f"{arch.bun}/bun", folder)
        binary.chmod(0o755)
    return binary, digest


def uv(pins: dict[str, str], arch: Arch, downloads: Path) -> tuple[Path, str]:
    name = f"uv-{arch.uv}.tar.gz"
    base = f"https://github.com/astral-sh/uv/releases/download/{pins['UV_VERSION']}"
    folder = downloads / f"uv-{pins['UV_VERSION']}"
    archive = download(f"{base}/{name}", folder / name)
    expected = download(f"{base}/{name}.sha256", folder / f"{name}.sha256").read_text(encoding="utf-8").split()[0]
    digest = checked(archive, expected)
    unpacked = folder / f"uv-{arch.uv}"
    if not (unpacked / "uv").exists():
        with tarfile.open(archive) as bundle:
            bundle.extractall(folder, filter="data")
    return unpacked, digest


def aidlc_workflows(pins: dict[str, str], work: Path, bun_bin: Path) -> Path:
    commit = pins["AIDLC_WORKFLOWS_BUILD_COMMIT"]
    checkout = work / f"aidlc-workflows-{commit[:12]}"
    built = checkout / ".bench-built"
    if built.exists():
        return checkout
    if not checkout.exists():
        run(["git", "clone", "--filter=blob:none", "--no-checkout", pins["AIDLC_WORKFLOWS_URL"], str(checkout)])
    run(["git", "-C", str(checkout), "checkout", "--detach", commit])
    run([str(bun_bin), "install", "--frozen-lockfile"], cwd=checkout, env=bun_env(bun_bin))
    run([str(bun_bin), "scripts/package.ts"], cwd=checkout, env=bun_env(bun_bin))
    built.write_text(commit + "\n", encoding="utf-8")
    return checkout


def plugin_projection(pins: dict[str, str], work: Path, bun_bin: Path, upstream: Path) -> Path:
    commit = pins["PLUGIN_COMMIT"]
    source = work / f"plugin-{commit[:12]}"
    projection = source / "security" / "dist" / "claude"
    if projection.exists():
        return projection
    if source.exists():
        shutil.rmtree(source)
    source.mkdir(parents=True)
    archive = subprocess.run(["git", "-C", str(pinfile.REPO), "archive", commit], capture_output=True, check=True)
    subprocess.run(["tar", "-x", "-C", str(source)], input=archive.stdout, check=True)
    env = {**bun_env(bun_bin), "AIDLC_WORKFLOWS_DIR": str(upstream)}
    run([str(bun_bin), "scripts/plugin-tool.ts", "build", "security", "claude"], cwd=source, env=env)
    return projection


def bun_env(bun_bin: Path) -> dict[str, str]:
    """The build tools also start `bun` by name (aidlc-workflows scripts/package.ts)."""
    return {**os.environ, "PATH": f"{bun_bin.parent}:{os.environ.get('PATH', '')}"}


def build(out: Path, work: Path, pins: dict[str, str]) -> dict:
    arch = host_arch()
    downloads = work / "downloads"
    bun_bin, bun_sha = bun(pins, arch, downloads)
    uv_dir, uv_sha = uv(pins, arch, downloads)
    release = aidlc_release(pins, arch, downloads)
    upstream = aidlc_workflows(pins, work, bun_bin)
    projection = plugin_projection(pins, work, bun_bin, upstream)

    staging = out.with_name(out.name + ".partial")
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(projection, staging / MARKETPLACE_DIR)
    release_dir = downloads / f"aidlc-{pins['AIDLC_VERSION']}-{arch.aidlc}"
    shutil.copytree(release_dir, staging / RELEASE_DIR)
    (staging / "bin").mkdir()
    shutil.copy2(bun_bin, staging / "bin" / "bun")
    for tool in ("uv", "uvx"):
        shutil.copy2(uv_dir / tool, staging / "bin" / tool)
    (staging / "pins.env").write_text("".join(f"{key}={pins[key]}\n" for key in CONTAINER_PINS), encoding="utf-8")
    manifest = {
        "built_at": pinfile.now(),
        "host": pinfile.host(),
        "arch": arch.aidlc,
        "plugin": {"commit": pins["PLUGIN_COMMIT"]},
        "aidlc_workflows_build": {"url": pins["AIDLC_WORKFLOWS_URL"], "commit": pinfile.git_head(upstream)},
        "aidlc_release": {"version": pins["AIDLC_VERSION"], "sha256": release},
        "bun": {"version": pins["BUN_VERSION"], "asset": f"{arch.bun}.zip", "sha256": bun_sha},
        "uv": {"version": pins["UV_VERSION"], "asset": f"uv-{arch.uv}.tar.gz", "sha256": uv_sha},
        "security_agent_mcp": pins["SECURITY_AGENT_MCP"],
        "security_agent_region": pins["SECURITY_AGENT_REGION"],
    }
    pinfile.write_json(staging / "manifest.json", manifest)
    if out.exists():
        shutil.rmtree(out)
    staging.rename(out)
    return manifest


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="build_assets.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--work", type=Path, help="cache for downloads and checkouts (default: next to --out)")
    parser.add_argument("--config", type=Path, default=pinfile.CONFIG)
    args = parser.parse_args(argv)
    out = args.out.resolve()
    manifest = build(out, (args.work or out.parent / "asset-cache").resolve(), pinfile.load(args.config))
    print(f"build-assets: wrote {out} (plugin {manifest['plugin']['commit'][:12]}, AI-DLC {manifest['aidlc_release']['version']})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
