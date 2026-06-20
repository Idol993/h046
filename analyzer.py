import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass
class FunctionMetrics:
    name: str
    complexity: int = 1
    start_line: int = 0
    end_line: int = 0
    lines: int = 0


@dataclass
class FileMetrics:
    path: str
    language: str
    total_lines: int = 0
    functions: List[FunctionMetrics] = field(default_factory=list)
    coupling: int = 0
    imports: List[str] = field(default_factory=list)

    @property
    def total_complexity(self) -> int:
        return sum(f.complexity for f in self.functions)

    @property
    def max_complexity(self) -> int:
        return max((f.complexity for f in self.functions), default=0)

    @property
    def max_function_lines(self) -> int:
        return max((f.lines for f in self.functions), default=0)


class PythonAnalyzer:
    def __init__(self, branch_keywords: List[str]):
        self.branch_keywords = set(branch_keywords)

    def _count_complexity(self, node: ast.AST) -> int:
        count = 0
        node_type = type(node).__name__
        if node_type in self.branch_keywords:
            count += 1
        if node_type == "BoolOp":
            values = getattr(node, "values", [])
            count += max(0, len(values) - 1)
        for child in ast.iter_child_nodes(node):
            count += self._count_complexity(child)
        return count

    def analyze(self, source: str, file_path: str) -> FileMetrics:
        tree = ast.parse(source)
        lines = source.splitlines()
        functions: List[FunctionMetrics] = []
        imports: List[str] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                else:
                    module = node.module or ""
                    imports.append(module)

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = node.name
                start_line = node.lineno
                end_line = getattr(node, "end_lineno", start_line)
                func_lines = end_line - start_line + 1
                complexity = 1 + self._count_complexity(node)
                functions.append(FunctionMetrics(
                    name=func_name,
                    complexity=complexity,
                    start_line=start_line,
                    end_line=end_line,
                    lines=func_lines,
                ))

        return FileMetrics(
            path=file_path,
            language="python",
            total_lines=len(lines),
            functions=functions,
            coupling=len(set(imports)),
            imports=imports,
        )


class RegexBasedAnalyzer:
    def __init__(self, language: str, branch_keywords: List[str]):
        self.language = language
        self.branch_keywords = branch_keywords

    def _build_branch_regex(self) -> str:
        escaped = [re.escape(kw) for kw in self.branch_keywords]
        return r"\b(" + "|".join(escaped) + r")\b"

    def _find_functions_js(self, lines: List[str]) -> List[Dict[str, Any]]:
        functions = []
        func_pattern = re.compile(
            r"(?:function\s+(\w+)\s*\(|(\w+)\s*[:=]\s*(?:async\s+)?(?:function\s*)?\(|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\()?"
        )
        i = 0
        while i < len(lines):
            line = lines[i]
            match = func_pattern.search(line)
            if match:
                name = match.group(1) or match.group(2) or match.group(3) or "anonymous"
                start = i + 1
                brace_count = 0
                found_brace = False
                j = i
                while j < len(lines):
                    for ch in lines[j]:
                        if ch == "{":
                            brace_count += 1
                            found_brace = True
                        elif ch == "}":
                            brace_count -= 1
                    if found_brace and brace_count == 0:
                        break
                    j += 1
                end = j + 1
                functions.append({"name": name, "start": start, "end": end})
                i = j
            i += 1
        return functions

    def _find_functions_java(self, lines: List[str]) -> List[Dict[str, Any]]:
        functions = []
        func_pattern = re.compile(
            r"(?:public|private|protected|static|final|synchronized|abstract|native|strictfp|\s)*(?:<[^>]+>\s*)?[\w<>\[\]]+\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{"
        )
        i = 0
        while i < len(lines):
            line = lines[i]
            match = func_pattern.search(line)
            if match:
                name = match.group(1)
                start = i + 1
                brace_count = 0
                found_brace = False
                j = i
                while j < len(lines):
                    for ch in lines[j]:
                        if ch == "{":
                            brace_count += 1
                            found_brace = True
                        elif ch == "}":
                            brace_count -= 1
                    if found_brace and brace_count == 0:
                        break
                    j += 1
                end = j + 1
                functions.append({"name": name, "start": start, "end": end})
                i = j
            i += 1
        return functions

    def _count_branches_in_range(self, lines: List[str], start: int, end: int) -> int:
        branch_re = self._build_branch_regex()
        count = 0
        for i in range(start - 1, min(end, len(lines))):
            line = lines[i]
            matches = re.findall(branch_re, line)
            count += len(matches)
            if "&&" in line or "||" in line:
                count += line.count("&&") + line.count("||")
            if "?" in line and ":" in line:
                count += 1
        return count

    def _find_imports(self, source: str) -> List[str]:
        imports = []
        if self.language == "javascript":
            for match in re.finditer(r"(?:import|require)\s*(?:\(|from\s+)?['\"]([^'\"]+)['\"]", source):
                imports.append(match.group(1))
        elif self.language == "java":
            for match in re.finditer(r"import\s+([\w.*]+);", source):
                imports.append(match.group(1))
        return imports

    def analyze(self, source: str, file_path: str) -> FileMetrics:
        lines = source.splitlines()
        imports = self._find_imports(source)

        if self.language == "javascript":
            raw_funcs = self._find_functions_js(lines)
        elif self.language == "java":
            raw_funcs = self._find_functions_java(lines)
        else:
            raw_funcs = []

        functions: List[FunctionMetrics] = []
        for rf in raw_funcs:
            func_lines = rf["end"] - rf["start"] + 1
            complexity = 1 + self._count_branches_in_range(lines, rf["start"], rf["end"])
            functions.append(FunctionMetrics(
                name=rf["name"],
                complexity=complexity,
                start_line=rf["start"],
                end_line=rf["end"],
                lines=func_lines,
            ))

        return FileMetrics(
            path=file_path,
            language=self.language,
            total_lines=len(lines),
            functions=functions,
            coupling=len(set(imports)),
            imports=imports,
        )


def get_analyzer(language: str, branch_keywords: List[str]):
    if language == "python":
        return PythonAnalyzer(branch_keywords)
    else:
        return RegexBasedAnalyzer(language, branch_keywords)


def analyze_file(file_path: Path, language: str, branch_keywords: List[str]) -> Optional[FileMetrics]:
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        analyzer = get_analyzer(language, branch_keywords)
        return analyzer.analyze(source, str(file_path))
    except (SyntaxError, UnicodeDecodeError, Exception):
        return None
