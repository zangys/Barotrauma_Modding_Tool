import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import deque

from Code.app_vars import AppConfig

logger = logging.getLogger(__name__)


class UserRulesManager:
    _rules: List[Dict[str, str]] = []
    _file_path: Optional[Path] = None

    @classmethod
    def init(cls) -> None:
        cls._file_path = AppConfig.get_data_root_path() / "user_rules.json"
        cls.load()

    @classmethod
    def load(cls) -> None:
        if not cls._file_path or not cls._file_path.exists():
            cls._rules = []
            return

        try:
            with open(cls._file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                cls._rules = data.get("rules", [])
        except Exception as e:
            logger.error(f"Failed to load user rules: {e}")
            cls._rules = []

    @classmethod
    def save(cls) -> None:
        if not cls._file_path:
            return

        try:
            with open(cls._file_path, "w", encoding="utf-8") as f:
                json.dump({"rules": cls._rules}, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save user rules: {e}")

    @classmethod
    def get_rules(cls) -> List[Dict[str, str]]:
        return cls._rules

    @classmethod
    def add_rule(cls, before_id: str, after_id: str) -> Tuple[bool, str]:
        """
        Adds a rule: Subject (before_id) should be HIGHER than Target (after_id).
        Logic: Subject depends on Target.
        """
        if before_id == after_id:
            return False, "Self-dependency is not allowed."

        # Check for duplicates
        for rule in cls._rules:
            if rule["subject"] == before_id and rule["target"] == after_id:
                return False, "Rule already exists."

        # Check for immediate conflict
        for rule in cls._rules:
            if rule["subject"] == after_id and rule["target"] == before_id:
                return False, "Conflict rule exists: A -> B and B -> A."

        # Check for Cycle (BFS)
        # We want to add dependency: Subject (A) depends on Target (B)
        # Edge: B -> A
        # Cycle exists if there is already a path from Subject back to Target
        if cls._check_path_exists(start_node=before_id, end_node=after_id):
            return False, "Circular dependency detected! This rule would create a loop."

        cls._rules.append({
            "action": "load_before",
            "subject": before_id,
            "target": after_id
        })
        cls.save()
        return True, "Success"

    @classmethod
    def remove_rule(cls, index: int) -> bool:
        if 0 <= index < len(cls._rules):
            cls._rules.pop(index)
            cls.save()
            return True
        return False

    @classmethod
    def clear_all(cls) -> None:
        cls._rules.clear()
        cls.save()

    @classmethod
    def _check_path_exists(cls, start_node: str, end_node: str) -> bool:
        # Build graph from current rules
        # Edge: Target -> Subject (Subject depends on Target)
        graph: Dict[str, List[str]] = {}
        for rule in cls._rules:
            u, v = rule["subject"], rule["target"]
            if v not in graph:
                graph[v] = []
            graph[v].append(u)

        # BFS
        queue = deque([start_node])
        visited = {start_node}

        while queue:
            curr = queue.popleft()
            if curr == end_node:
                return True

            if curr in graph:
                for neighbor in graph[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

        return False
