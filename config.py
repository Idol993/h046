import os
import fnmatch
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yaml"
DEBTIGNORE_FILENAME = ".debtignore"


class Config:
    def __init__(
        self,
        config_path: Optional[Path] = None,
        project_root: Optional[Path] = None,
        scan_root: Optional[Path] = None,
    ):
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.scan_root = Path(scan_root) if scan_root else self.project_root
        self._data: Dict[str, Any] = {}
        self._ignore_patterns: List[str] = []
        self.load()
        self.load_debtignore()

    def _resolve_rel(self, file_path: Path) -> str:
        if file_path.is_absolute():
            for root in (self.scan_root, self.project_root):
                try:
                    return str(file_path.relative_to(root)).replace("\\", "/")
                except ValueError:
                    continue
            return file_path.name
        return str(file_path).replace("\\", "/")

    def _resolve_rel_all(self, file_path: Path) -> List[str]:
        results = []
        if file_path.is_absolute():
            for root in (self.scan_root, self.project_root):
                try:
                    results.append(str(file_path.relative_to(root)).replace("\\", "/"))
                except ValueError:
                    continue
            if not results:
                results.append(file_path.name)
        else:
            results.append(str(file_path).replace("\\", "/"))
        return results

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
        rel_paths = self._resolve_rel_all(file_path)
        for rel_str in rel_paths:
            filename = Path(rel_str).name
            for pattern in self._ignore_patterns:
                if "/" in pattern:
                    if fnmatch.fnmatch(rel_str, pattern) or fnmatch.fnmatch(rel_str, f"{pattern.rstrip('/')}/**"):
                        return True
                else:
                    if fnmatch.fnmatch(filename, pattern):
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

    def get_overrides(self) -> List[Dict[str, Any]]:
        return self._data.get("overrides", []) or []

    def _match_pattern(self, rel_str: str, pattern: str) -> bool:
        rel_norm = rel_str.replace("\\", "/")
        pat_norm = pattern.replace("\\", "/").lstrip("/")
        if fnmatch.fnmatch(rel_norm, pat_norm):
            return True
        if fnmatch.fnmatch(rel_norm, f"{pat_norm.rstrip('/')}/**"):
            return True
        base = rel_norm.split("/", 1)[0] if "/" in rel_norm else rel_norm
        return False

    def get_effective_config(
        self, file_path: Path, language: str
    ) -> Dict[str, Any]:
        rel_paths = self._resolve_rel_all(file_path)

        lang_cfg = self.get_language_config(language) or {}
        result = {
            "source": "default",
            "source_pattern": None,
            "source_description": None,
            "threshold": dict(lang_cfg.get("threshold", {})),
            "penalty": dict(lang_cfg.get("penalty", {})),
            "resolved_path": self._resolve_rel(file_path),
        }

        applied = []
        for override in self.get_overrides():
            pattern = override.get("pattern", "")
            allowed_langs = override.get("languages")
            if allowed_langs and language not in allowed_langs:
                continue
            if not pattern:
                continue
            matched = False
            for rel_str in rel_paths:
                if self._match_pattern(rel_str, pattern):
                    matched = True
                    break
            if not matched:
                continue
            applied.append(override)

        for override in applied:
            override_threshold = override.get("threshold", {}) or {}
            override_penalty = override.get("penalty", {}) or {}
            for k, v in override_threshold.items():
                result["threshold"][k] = v
            for k, v in override_penalty.items():
                result["penalty"][k] = v
            result["source"] = "override"
            result["source_pattern"] = override.get("pattern")
            result["source_description"] = override.get("description")

        return result

    def get_effective_threshold(self, file_path: Path, language: str, metric: str) -> int:
        eff = self.get_effective_config(file_path, language)
        return eff["threshold"].get(metric, 0)

    def get_effective_penalty(self, file_path: Path, language: str, metric: str) -> int:
        eff = self.get_effective_config(file_path, language)
        return eff["penalty"].get(metric, 0)
