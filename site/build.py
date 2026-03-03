#!/usr/bin/env python3
"""Static site generator for Study Materials.

Converts markdown content into a static HTML site suitable for
GitHub Pages hosting alongside a Jekyll site.

Usage:
    python site/build.py                         # Build to ../05_CV/study/
    python site/build.py -o ./dist               # Build to custom dir
    python site/build.py --base-url /study       # Set base URL prefix
    python site/build.py --clean                 # Clean output before build
"""

import argparse
import os
import shutil
import sys
import time
import urllib.request
from pathlib import Path

# Ensure the site package is importable by adding site/ dir to path
_site_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(_site_dir))
# Add project root for shared/ package
sys.path.insert(0, str(_site_dir.parent))

from config import BuildConfig
from builders.assets import AssetBuilder
from builders.content import ContentBuilder
from builders.index import IndexBuilder
from builders.examples import ExampleBuilder
from builders.paths import PathsBuilder
from builders.search import SearchBuilder

LUNR_CDN_URL = "https://unpkg.com/lunr@2.3.9/lunr.min.js"


def download_lunr(output_dir: Path):
    """Download lunr.min.js if not already present."""
    lunr_path = output_dir / "static" / "js" / "lunr.min.js"
    if lunr_path.exists() and lunr_path.stat().st_size > 1000:
        return  # Already downloaded

    print("  Downloading lunr.min.js...")
    lunr_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        urllib.request.urlretrieve(LUNR_CDN_URL, lunr_path)
        print(f"  Downloaded lunr.min.js ({lunr_path.stat().st_size:,} bytes)")
    except Exception as e:
        print(f"  Warning: Could not download lunr.js: {e}")
        print("  Search will not work without lunr.min.js")
        print(f"  Manual download: curl -o {lunr_path} {LUNR_CDN_URL}")


def main():
    parser = argparse.ArgumentParser(description="Build static study site")
    parser.add_argument(
        "--output",
        "-o",
        default=str(Path(__file__).parent.parent.parent / "05_CV" / "study"),
        help="Output directory (default: ../../05_CV/study)",
    )
    parser.add_argument(
        "--base-url",
        default="/study",
        help="Base URL path prefix (default: /study)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean output directory before building",
    )
    parser.add_argument(
        "--content-dir",
        default=None,
        help="Path to study_hub content root (default: STUDY_HUB_PATH env or ../)",
    )
    args = parser.parse_args()

    study_hub = Path(args.content_dir) if args.content_dir else Path(
        os.environ.get("STUDY_HUB_PATH", str(_site_dir.parent))
    )

    config = BuildConfig(
        content_dir=study_hub / "content",
        examples_dir=study_hub / "examples",
        output_dir=Path(args.output).resolve(),
        base_url=args.base_url,
    )

    print(f"Building static site...")
    print(f"  Content: {config.content_dir}")
    print(f"  Examples: {config.examples_dir}")
    print(f"  Output: {config.output_dir}")
    print(f"  Base URL: {config.base_url}")
    print()

    if args.clean and config.output_dir.exists():
        print("Cleaning output directory...")
        shutil.rmtree(config.output_dir)

    config.output_dir.mkdir(parents=True, exist_ok=True)

    start = time.time()

    # Phase 1: Static assets
    print("[1/6] Copying static assets...")
    AssetBuilder(config).build()
    download_lunr(config.output_dir)

    # Phase 2: Render lesson pages
    print("[2/6] Building lesson pages...")
    ContentBuilder(config).build()

    # Phase 3: Generate index/topic pages
    print("[3/6] Building index pages...")
    IndexBuilder(config).build()

    # Phase 4: Generate example viewer pages
    print("[4/6] Building example pages...")
    ExampleBuilder(config).build()

    # Phase 5: Generate learning path pages
    print("[5/6] Building learning path pages...")
    PathsBuilder(config).build()

    # Phase 6: Build search index
    print("[6/6] Building search index...")
    SearchBuilder(config).build()

    # Create .nojekyll marker (harmless even inside Jekyll site)
    (config.output_dir / ".nojekyll").touch()

    elapsed = time.time() - start
    print(f"\nBuild complete in {elapsed:.1f}s")
    print(f"Output: {config.output_dir}")

    # Count generated files
    html_count = sum(1 for _ in config.output_dir.rglob("*.html"))
    print(f"Generated {html_count} HTML files")


if __name__ == "__main__":
    main()
