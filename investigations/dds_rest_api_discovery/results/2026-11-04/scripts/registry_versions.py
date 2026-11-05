#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["rich>=13.9"]
# ///
"""Shows a node registry's volley versions, newest first: build time, GITSHA, and which images each has.

    uv run registry_versions.py [HOST:PORT] [--highlight PREFIX ...]
"""

import argparse
import json
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone

from rich.console import Console
from rich.progress import Progress
from rich.table import Table
from rich.text import Text

IMAGES = ("bay", "central", "control", "mapserver", "noc")
ACCEPT = ",".join(
    f"application/vnd.{kind}"
    for kind in (
        "oci.image.index.v1+json",
        "oci.image.manifest.v1+json",
        "docker.distribution.manifest.v2+json",
        "docker.distribution.manifest.list.v2+json",
    )
)


@dataclass(frozen=True)
class Version:
    name: str
    images: frozenset[str]
    built: datetime | None
    gitsha: str
    error: str = ""


def get(url: str) -> dict:
    request = urllib.request.Request(url, headers={"Accept": ACCEPT})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def image_config(base: str, tag: str) -> dict:
    manifest = get(f"{base}/manifests/{tag}")
    if "manifests" in manifest:
        platform = next(
            m
            for m in manifest["manifests"]
            if m.get("platform", {}).get("architecture") != "unknown"
        )
        manifest = get(f"{base}/manifests/{platform['digest']}")
    return get(f"{base}/blobs/{manifest['config']['digest']}")


def describe(base: str, name: str, images: frozenset[str]) -> Version:
    try:
        config = image_config(base, f"{min(images)}-{name}")
    except Exception as error:  # noqa: BLE001 - one bad tag shouldn't hide the rest
        return Version(name, images, None, "-", str(error))
    env = config.get("config", {}).get("Env", [])
    gitsha = next((e.removeprefix("GITSHA=") for e in env if e.startswith("GITSHA=")), "-")
    built = datetime.fromisoformat(config["created"]) if "created" in config else None
    return Version(name, images, built, gitsha)


def versions_by_name(base: str) -> dict[str, frozenset[str]]:
    versions: dict[str, set[str]] = defaultdict(set)
    for tag in get(f"{base}/tags/list")["tags"]:
        image, _, name = tag.partition("-")
        if image in IMAGES:
            versions[name].add(image)
    return {name: frozenset(images) for name, images in versions.items()}


def age(built: datetime | None, now: datetime) -> Text:
    if built is None:
        return Text("?", style="red")
    days = (now - built).total_seconds() / 86400
    label = f"{days * 24:.0f} h" if days < 1 else f"{days:.0f} d"
    style = "green" if days < 1 else "yellow" if days < 7 else "dim"
    return Text(label, style=style)


def image_cells(images: frozenset[str]) -> list[Text]:
    return [Text("●", style="green") if i in images else Text("✗", style="bold red") for i in IMAGES]


def table(host: str, versions: list[Version], highlight: list[str]) -> Table:
    now = datetime.now(timezone.utc)
    result = Table(
        title=f"volley images in {host}",
        caption=f"{len(versions)} versions · ● present  ✗ missing",
        header_style="bold",
        row_styles=["", "on grey11"],
    )
    result.add_column("Built", no_wrap=True)
    result.add_column("Age", justify="right")
    result.add_column("Version")
    result.add_column("GITSHA", style="cyan")
    for image in IMAGES:
        result.add_column(image, justify="center")
    for version in versions:
        is_highlighted = any(version.name.startswith(prefix) for prefix in highlight)
        name = Text(version.name, style="bold magenta" if is_highlighted else "")
        if version.error:
            name.append(f"  {version.error}", style="red")
        built = version.built.astimezone().strftime("%Y-%m-%d %H:%M") if version.built else "-"
        result.add_row(built, age(version.built, now), name, version.gitsha, *image_cells(version.images))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("host", nargs="?", default="central-comb:4000")
    parser.add_argument("--highlight", action="append", default=None, help="version prefix to highlight (default: dds-diag-)")
    args = parser.parse_args()
    base = f"http://{args.host}/v2/volley"
    console = Console()

    names = versions_by_name(base)
    with Progress(console=console, transient=True) as progress, ThreadPoolExecutor(8) as pool:
        task = progress.add_task("Reading image configs", total=len(names))
        futures = [pool.submit(describe, base, name, images) for name, images in names.items()]
        for future in futures:
            future.add_done_callback(lambda _: progress.advance(task))
        versions = [future.result() for future in futures]

    oldest = datetime.min.replace(tzinfo=timezone.utc)
    versions.sort(key=lambda v: v.built or oldest, reverse=True)
    console.print(table(args.host, versions, args.highlight or ["dds-diag-"]))


if __name__ == "__main__":
    main()
