from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Optional

from core.models import FramePacket


@dataclass
class SharedFrameState:
    latest: Optional[FramePacket] = None
    lock: threading.Lock = field(default_factory=threading.Lock)
