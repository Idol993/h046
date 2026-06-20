import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import Config
from scorer import ProjectScore, FileScore, DeductionItem


TEMPLATES_DIR = Path(__file__).parent / "templates"


class Reporter:
    def __init__(self, config: Config):
        self.config = config
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def _file_to_dict(self, file_score: FileScore) -> Dict[str, Any]:
        return {
            "path": file_score.path,
            "language": file_score.language,
            "total_lines": file_score.total_lines,
            "total_penalty": file_score.total_penalty,
            "has_violations": file_score.has_violations,
            "rule_source": file_score.rule_source,
            "rule_pattern": file_score.rule_pattern,
            "rule_description": file_score.rule_description,
            "function_details": file_score.function_details,
            "deductions": [
                {
                    "metric": d.metric,
                    "value": d.value,
                    "threshold": d.threshold,
                    "penalty": d.penalty,
                    "function_name": d.function_name,
                    "start_line": d.start_line,
                    "end_line": d.end_line,
                    "is_over": d.is_over,
                    "rule_source": d.rule_source,
                    "rule_pattern": d.rule_pattern,
                    "rule_description": d.rule_description,
                }
                for d in file_score.deductions
            ],
        }

    def generate_json(self, project_score: ProjectScore, threshold: int, output_path: Path) -> None:
        report = {
            "generated_at": datetime.now().isoformat(),
            "threshold": threshold,
            "total_penalty": project_score.total_penalty,
            "total_files": len(project_score.files),
            "violation_files": len(project_score.files_with_violations),
            "total_lines": project_score.total_lines,
            "top_functions": project_score.top_functions[:20],
            "files": [self._file_to_dict(f) for f in project_score.files],
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    def _build_charts_data(self, project_score: ProjectScore) -> Dict[str, Any]:
        lang_counts: Dict[str, int] = {}
        for f in project_score.files:
            lang_counts[f.language] = lang_counts.get(f.language, 0) + 1

        sorted_files = sorted(project_score.files, key=lambda x: x.total_penalty, reverse=True)[:10]
        top_files_labels = [Path(f.path).name for f in sorted_files]
        top_files_data = [f.total_penalty for f in sorted_files]

        violation_counts = {"complexity": 0, "function_lines": 0, "coupling": 0}
        for f in project_score.files:
            for d in f.deductions:
                if d.is_over and d.metric in violation_counts:
                    violation_counts[d.metric] += 1

        return {
            "languages": {
                "labels": json.dumps(list(lang_counts.keys()), ensure_ascii=False),
                "data": json.dumps(list(lang_counts.values())),
            },
            "top_files": {
                "labels": json.dumps(top_files_labels, ensure_ascii=False),
                "data": json.dumps(top_files_data),
            },
            "violations": {
                "labels": json.dumps(["圈复杂度", "函数行数", "文件耦合度"], ensure_ascii=False),
                "data": json.dumps([
                    violation_counts["complexity"],
                    violation_counts["function_lines"],
                    violation_counts["coupling"],
                ]),
            },
        }

    def _get_thresholds(self) -> Dict[str, Dict[str, int]]:
        thresholds = {}
        for lang in self.config.get_languages():
            thresholds[lang] = {
                "complexity": self.config.get_threshold(lang, "complexity"),
                "function_lines": self.config.get_threshold(lang, "function_lines"),
                "coupling": self.config.get_threshold(lang, "coupling"),
            }
        return thresholds

    def _get_effective_thresholds(self, project_score: ProjectScore) -> Dict[str, Dict[str, int]]:
        result = {}
        for f in project_score.files:
            key = f.path
            lang = f.language
            default_complexity = self.config.get_threshold(lang, "complexity")
            default_lines = self.config.get_threshold(lang, "function_lines")
            default_coupling = self.config.get_threshold(lang, "coupling")
            eff = self.config.get_effective_config(Path(key), lang)
            result[key] = {
                "complexity": eff["threshold"].get("complexity", default_complexity),
                "function_lines": eff["threshold"].get("function_lines", default_lines),
                "coupling": eff["threshold"].get("coupling", default_coupling),
            }
        return result

    def generate_html(
        self, project_score: ProjectScore, threshold: int, output_path: Path
    ) -> None:
        template = self.env.get_template("report.html")
        all_files_sorted = sorted(
            project_score.files,
            key=lambda x: (-x.total_penalty, x.path),
        )
        charts_data = self._build_charts_data(project_score)
        thresholds = self._get_thresholds()
        effective_thresholds = self._get_effective_thresholds(project_score)

        html = template.render(
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_penalty=project_score.total_penalty,
            total_files=len(project_score.files),
            violation_files=len(project_score.files_with_violations),
            total_lines=project_score.total_lines,
            threshold=threshold,
            files_with_violations=sorted(
                project_score.files_with_violations,
                key=lambda x: (-x.total_penalty, x.path),
            ),
            all_files_sorted=all_files_sorted,
            charts_data=charts_data,
            thresholds=thresholds,
            effective_thresholds=effective_thresholds,
        )
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

    def generate(
        self,
        project_score: ProjectScore,
        output_format: str,
        output_path: Path,
        threshold: int,
    ) -> None:
        output_format = output_format.lower()
        if output_format == "json":
            self.generate_json(project_score, threshold, output_path)
        elif output_format == "html":
            self.generate_html(project_score, threshold, output_path)
        else:
            raise ValueError(f"Unsupported format: {output_format}")
