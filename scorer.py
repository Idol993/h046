from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any

from analyzer import FileMetrics, FunctionMetrics
from config import Config


@dataclass
class DeductionItem:
    metric: str
    value: int
    threshold: int
    penalty: int
    function_name: str = ""
    start_line: int = 0
    end_line: int = 0
    rule_source: str = "default"
    rule_pattern: str = ""
    rule_description: str = ""

    @property
    def is_over(self) -> bool:
        return self.value > self.threshold


@dataclass
class FileScore:
    path: str
    language: str
    total_lines: int
    rule_source: str = "default"
    rule_pattern: str = ""
    rule_description: str = ""
    deductions: List[DeductionItem] = field(default_factory=list)
    function_details: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def total_penalty(self) -> int:
        return sum(d.penalty for d in self.deductions)

    @property
    def has_violations(self) -> bool:
        return any(d.is_over for d in self.deductions)


@dataclass
class ProjectScore:
    files: List[FileScore] = field(default_factory=list)

    @property
    def total_penalty(self) -> int:
        return sum(f.total_penalty for f in self.files)

    @property
    def total_lines(self) -> int:
        return sum(f.total_lines for f in self.files)

    @property
    def files_with_violations(self) -> List[FileScore]:
        return [f for f in self.files if f.has_violations]

    @property
    def by_language(self) -> Dict[str, List[FileScore]]:
        result: Dict[str, List[FileScore]] = {}
        for f in self.files:
            result.setdefault(f.language, []).append(f)
        return result

    @property
    def top_functions(self) -> List[Dict[str, Any]]:
        func_deductions: List[Dict[str, Any]] = []
        for f in self.files:
            for d in f.deductions:
                if d.is_over and d.function_name:
                    func_deductions.append({
                        "file_path": f.path,
                        "language": f.language,
                        "function_name": d.function_name,
                        "metric": d.metric,
                        "value": d.value,
                        "threshold": d.threshold,
                        "penalty": d.penalty,
                        "start_line": d.start_line,
                        "end_line": d.end_line,
                        "rule_source": d.rule_source,
                        "rule_pattern": d.rule_pattern,
                        "rule_description": d.rule_description,
                    })
        func_deductions.sort(
            key=lambda x: (
                -x["penalty"],
                -x["value"],
                x["file_path"],
                x["function_name"],
                x["metric"],
            )
        )
        return func_deductions


class Scorer:
    def __init__(self, config: Config):
        self.config = config

    def _evaluate_function(
        self, func: FunctionMetrics, language: str, path: str,
        eff_threshold: Dict[str, int], eff_penalty: Dict[str, int],
        rule_source: str, rule_pattern: str, rule_description: str,
    ) -> List[DeductionItem]:
        deductions = []

        complexity_threshold = eff_threshold.get("complexity", 0)
        complexity_penalty = eff_penalty.get("complexity", 0)
        if func.complexity > complexity_threshold:
            deductions.append(DeductionItem(
                metric="complexity",
                value=func.complexity,
                threshold=complexity_threshold,
                penalty=complexity_penalty,
                function_name=func.name,
                start_line=func.start_line,
                end_line=func.end_line,
                rule_source=rule_source,
                rule_pattern=rule_pattern,
                rule_description=rule_description,
            ))

        lines_threshold = eff_threshold.get("function_lines", 0)
        lines_penalty = eff_penalty.get("function_lines", 0)
        if func.lines > lines_threshold:
            deductions.append(DeductionItem(
                metric="function_lines",
                value=func.lines,
                threshold=lines_threshold,
                penalty=lines_penalty,
                function_name=func.name,
                start_line=func.start_line,
                end_line=func.end_line,
                rule_source=rule_source,
                rule_pattern=rule_pattern,
                rule_description=rule_description,
            ))

        return deductions

    def _evaluate_file(self, metrics: FileMetrics) -> FileScore:
        language = metrics.language
        file_path = Path(metrics.path)
        eff = self.config.get_effective_config(file_path, language)
        eff_threshold: Dict[str, int] = eff["threshold"]
        eff_penalty: Dict[str, int] = eff["penalty"]
        rule_source = eff["source"]
        rule_pattern = eff.get("source_pattern") or ""
        rule_description = eff.get("source_description") or ""

        file_score = FileScore(
            path=metrics.path,
            language=language,
            total_lines=metrics.total_lines,
            rule_source=rule_source,
            rule_pattern=rule_pattern,
            rule_description=rule_description,
        )

        for func in metrics.functions:
            file_score.function_details.append({
                "name": func.name,
                "complexity": func.complexity,
                "lines": func.lines,
                "start_line": func.start_line,
                "end_line": func.end_line,
            })
            deductions = self._evaluate_function(
                func, language, metrics.path,
                eff_threshold, eff_penalty,
                rule_source, rule_pattern, rule_description,
            )
            file_score.deductions.extend(deductions)

        coupling_threshold = eff_threshold.get("coupling", 0)
        coupling_penalty = eff_penalty.get("coupling", 0)
        if metrics.coupling > coupling_threshold:
            file_score.deductions.append(DeductionItem(
                metric="coupling",
                value=metrics.coupling,
                threshold=coupling_threshold,
                penalty=coupling_penalty,
                function_name="",
                rule_source=rule_source,
                rule_pattern=rule_pattern,
                rule_description=rule_description,
            ))

        return file_score

    def score(self, all_metrics: List[FileMetrics]) -> ProjectScore:
        project_score = ProjectScore()
        for metrics in all_metrics:
            if metrics is not None:
                file_score = self._evaluate_file(metrics)
                project_score.files.append(file_score)
        return project_score
