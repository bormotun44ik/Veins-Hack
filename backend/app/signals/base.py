from abc import ABC, abstractmethod
import sqlite3

class BaseSignal(ABC):
    @abstractmethod
    def compute(self, person_id: str, conn: sqlite3.Connection) -> float:
        """Returns 0.0-1.0. 0=healthy, 1=critical. Never raises."""
        pass
