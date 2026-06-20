import os
import fnmatch
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yaml"
DEBTIGNORE_FILENAME = ".debtignore"


class Config:
    def __init__(self, config_path: Optional[Path] = None, project_root: Optional[Path] = None):
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self._data: Dict[str, Any] = {}
        self._ignore_patterns: List[str] = []
        self.load()
        self.load_debtignore()

    def load(self) -> None:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}
        else:
            self._data = {}

    def load_debtignore(self) -> None:
        debtignore_path = self.project_root / DEBTIGNORE_FILENAME
        if debtignore_path.exists():
            with open(debtignore_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        self._ignore_patterns.append(line)

    def is_ignored(self, file_path: Path) -> bool:
        rel_path = file_path.relative_to(self.project_root) if file_path.is_absolute() else file_path
        rel_str = str(rel_path).replace("\\", "/")
        for pattern in self._ignore_patterns:
            if fnmatch.fnmatch(rel_str, pattern) or fnmatch.fnmatch(rel_str, f"{pattern.rstrip('/')}/**"):
                return True
            if fnmatch.fnmatch(Path(rel_str).name, pattern):
                return True
        return False

    def get_languages(self) -> Dict[str, Dict[str, Any]]:
        return self._data.get("languages", {})

    def get_language_config(self, lang: str) -> Optional[Dict[str, Any]]:
        return self.get_languages().get(lang)

    def get_extensions(self, lang: str) -> List[str]:
        lang_config = self.get_language_config(lang)
        return lang_config.get("extensions", []) if lang_config else []

    def get_all_extensions(self) -> Dict[str, List[str]]:
        result = {}
        for lang, cfg in self.get_languages().items():
            result[lang] = cfg.get("extensions", [])
        return result

    def get_threshold(self, lang: str, metric: str) -> int:
        lang_config = self.get_language_config(lang)
        if lang_config:
            return lang_config.get("threshold", {}).get(metric, 0)
        return 0

    def get_penalty(self, lang: str, metric: str) -> int:
        lang_config = self.get_language_config(lang)
        if lang_config:
            return lang_config.get("penalty", {}).get(metric, 0)
        return 0

    def get_branch_keywords(self, lang: str) -> List[str]:
        lang_config = self.get_language_config(lang)
        return lang_config.get("branch_keywords", []) if lang_config else []

    def detect_language(self, file_path: Path) -> Optional[str]:
        suffix = file_path.suffix.lower()
        for lang, exts in self.get_all_extensions().items():
            if suffix in [e.lower() for e in exts]:
                return lang
        return None

    def get_default_language(self) -> str:
        return self._data.get("default_language", "python")

    def get_scan_depth(self) -> int:
        return self._data.get("scan_depth", 10)
