from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook

from core.timing import now_s


@dataclass
class CompetitionSession:
    team_name: str = ""
    duration_minutes: int = 10
    active: bool = False
    started_at_s: float | None = None
    started_at_iso: str | None = None
    runs: list[float] = field(default_factory=list)
    export_done: bool = False
    session_id: str = ""
    backup_path: Path | None = None

    def start(self, team_name: str, duration_minutes: int, output_dir: Path = Path("exports")) -> None:
        self.team_name = team_name.strip() or "UnknownTeam"
        self.duration_minutes = max(1, int(duration_minutes))
        self.active = True
        self.started_at_s = now_s()
        self.started_at_iso = datetime.now().isoformat(timespec="seconds")
        self.runs = []
        self.export_done = False

        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_team = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in self.team_name)
        safe_team = safe_team.encode("utf-8")[:100].decode("utf-8", errors="ignore") or "UnknownTeam"
        self.session_id = f"{safe_team}_{ts}"

        # Auto-save Setup
        try:
            exports_dir = output_dir
            exports_dir.mkdir(parents=True, exist_ok=True)
            self.backup_path = exports_dir / f"{self.session_id}_backup.csv"
            with open(self.backup_path, "w", encoding="utf-8") as f:
                f.write("Run No,Elapsed (s)\n")
        except Exception:
            self.backup_path = None

    def stop(self) -> None:
        self.active = False

    def add_run(self, elapsed_s: float) -> int:
        self.runs.append(elapsed_s)
        run_no = len(self.runs)

        # Auto-save Appending
        if self.backup_path is not None:
            try:
                with open(self.backup_path, "a", encoding="utf-8") as f:
                    f.write(f"{run_no},{round(elapsed_s, 3)}\n")
            except Exception:
                pass

        return run_no

    def best_time_s(self) -> float | None:
        if not self.runs:
            return None
        return min(self.runs)

    def remaining_seconds(self) -> float:
        if not self.active or self.started_at_s is None:
            return 0.0
        total = float(self.duration_minutes * 60)
        return max(0.0, total - (now_s() - self.started_at_s))

    def is_time_up(self) -> bool:
        return self.active and self.remaining_seconds() <= 0.0

    def export_excel(self, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)

        if not self.session_id:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            safe_team = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in self.team_name)
            safe_team = safe_team.encode("utf-8")[:100].decode("utf-8", errors="ignore") or "UnknownTeam"
            self.session_id = f"{safe_team}_{ts}"

        out_path = output_dir / f"{self.session_id}.xlsx"

        wb = Workbook()
        ws = wb.active
        ws.title = "CompetitionResult"
        ws.append(["Team Name", self.team_name])
        ws.append(["Duration (minutes)", self.duration_minutes])
        ws.append(["Session Start", self.started_at_iso or ""])
        ws.append(["Total Runs", len(self.runs)])
        best = self.best_time_s()
        ws.append(["Best Time (s)", "" if best is None else round(best, 3)])
        ws.append([])
        ws.append(["Run No", "Elapsed (s)", "Elapsed (ms)"])
        for i, t in enumerate(self.runs, start=1):
            ws.append([i, round(t, 3), round(t * 1000.0, 1)])

        wb.save(out_path)
        self.export_done = True
        return out_path
