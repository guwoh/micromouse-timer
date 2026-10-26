from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


PACKAGE = "micromouse-timer"
VERSION = "1.2.2"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    bundle = root / "dist" / "MicromouseTimer"
    executable = bundle / "MicromouseTimer"
    icon = root / "assets" / "icons" / "micromouse.png"
    if not executable.is_file() or not icon.is_file():
        raise SystemExit("Build MicromouseTimer.spec and generate the icon first.")
    if not shutil.which("dpkg-deb"):
        raise SystemExit("dpkg-deb is required to build the Linux installer.")

    output = root / "dist" / f"{PACKAGE}_{VERSION}_amd64.deb"
    with tempfile.TemporaryDirectory(prefix="micromouse-deb-") as temp:
        stage = Path(temp)
        app_dir = stage / "opt" / PACKAGE
        shutil.copytree(bundle, app_dir, symlinks=True)
        (stage / "usr" / "bin").mkdir(parents=True)
        (stage / "usr" / "bin" / PACKAGE).symlink_to(f"/opt/{PACKAGE}/MicromouseTimer")

        desktop_dir = stage / "usr" / "share" / "applications"
        desktop_dir.mkdir(parents=True)
        (desktop_dir / f"{PACKAGE}.desktop").write_text(
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=Micromouse Timer\n"
            "Comment=Time Micromouse robot runs\n"
            f"Exec=/opt/{PACKAGE}/MicromouseTimer\n"
            f"Icon={PACKAGE}\n"
            "Terminal=false\n"
            "Categories=Utility;\n"
            "Keywords=Micromouse;Timer;Competition;\n",
            encoding="utf-8",
        )

        icon_dir = stage / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps"
        icon_dir.mkdir(parents=True)
        shutil.copy2(icon, icon_dir / f"{PACKAGE}.png")

        control_dir = stage / "DEBIAN"
        control_dir.mkdir()
        (control_dir / "control").write_text(
            f"Package: {PACKAGE}\n"
            f"Version: {VERSION}\n"
            "Section: science\n"
            "Priority: optional\n"
            "Architecture: amd64\n"
            "Maintainer: Micromouse Timer Project\n"
            "Depends: libc6 (>= 2.39), libxcb-cursor0\n"
            "Description: Desktop timer for Micromouse competitions\n"
            " Detects robot motion at the start and goal using a camera.\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["dpkg-deb", "--build", "--root-owner-group", str(stage), str(output)],
            check=True,
        )
    print(output)


if __name__ == "__main__":
    main()
