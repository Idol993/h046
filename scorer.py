from dataclasses import dataclass, field
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

    @property
    def is_over(self) -> bool:
        return self.value > self.threshold


@dataclass
class FileScore:
    path: str
    language: str
    total_lines: int
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


class Scorer:
    def __init__(self, config: Config):
        self.config = config

    def _evaluate_function(
        self, func: FunctionMetrics, language: str, path: str
    ) -> List[DeductionItem]:
        deductions = []

        complexity_threshold = self.config.get_threshold(language, "complexity")
        complexity_penalty = self.config.get_penalty(language, "complexity")
        if func.complexity > complexity_threshold:
            deductions.append(DeductionItem(
                metric="complexity",
                value=func.complexity,
                threshold=complexity_threshold,
                penalty=complexity_penalty,
                function_name=func.name,
            ))

        lines_threshold = self.config.get_threshold(language, "function_lines")
        lines_penalty = self.config.get_penalty(language, "function_lines")
        if func.lines > lines_threshold:
            deductions.append(DeductionItem(
                metric="function_lines",
                value=func.lines,
                threshold=lines_threshold,
                penalty=lines_penalty,
                function_name=func.name,
            ))

        return deductions

    def _evaluate_file(self, metrics: FileMetrics) -> FileScore:
        language = metrics.language
        file_score = FileScore(
            path=metrics.path,
            language=language,
            total_lines=metrics.total_lines,
        )

        for func in metrics.functions:
            file_score.function_details.append({
                "name": func.name,
                "complexity": func.complexity,
                "lines": func.lines,
                "start_line": func.start_line,
                "end_line": func.end_line,
            })
            deductions = self._evaluate_function(func, language, metrics.path)
            file_score.deductions.extend(deductions)

        coupling_threshold = self.config.get_threshold(language, "coupling")
        coupling_penalty = self.config.get_penalty(language, "coupling")
        if metrics.coupling > coupling_threshold:
            file_score.deductions.append(DeductionItem(
                metric="coupling",
                value=metrics.coupling,
                threshold=coupling_threshold,
                penalty=coupling_penalty,
                function_name="",
            ))

        return file_score

    def score(self, all_metrics: List[FileMetrics]) -> ProjectScore:
        project_score = ProjectScore()
        for metrics in all_metrics:
            if metrics is not None:
                file_score = self._evaluate_file(metrics)
                project_score.files.append(file_score)
        return project_score
