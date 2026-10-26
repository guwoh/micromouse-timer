from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import numpy as np


class CameraSource(ABC):
    @abstractmethod
    def open(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def read(self) -> tuple[bool, Optional[np.ndarray]]:
        raise NotImplementedError

    @abstractmethod
    def release(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_opened(self) -> bool:
        raise NotImplementedError
