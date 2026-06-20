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


class _BraceBalancer:
    @staticmethod
    def find_block_end(lines: List[str], start_idx: int) -> int:
        brace_count = 0
        found = False
        j = start_idx
        while j < len(lines):
            line = lines[j]
            in_string = False
            string_char = None
            escaped = False
            k = 0
            while k < len(line):
                ch = line[k]
                if escaped:
                    escaped = False
                    k += 1
                    continue
                if ch == '\\':
                    escaped = True
                    k += 1
                    continue
                if in_string:
                    if ch == string_char:
                        in_string = False
                    k += 1
                    continue
                if ch in ('"', "'", '`'):
                    in_string = True
                    string_char = ch
                    k += 1
                    continue
                if ch in ('{', '(', '['):
                    brace_count += 1
                    found = True
                elif ch in ('}', ')', ']'):
                    brace_count -= 1
                k += 1
            if found and brace_count <= 0:
                return j
            j += 1
        return len(lines) - 1


class JavaScriptAnalyzer:
    _FUNC_PATTERNS = [
        re.compile(
            r"""(?:export\s+)?(?:default\s+)?(?:async\s+)?
                function\s+(\w+)\s*\(""",
            re.VERBOSE,
        ),
        re.compile(
            r"""(?:export\s+)?(?:default\s+)?
                (?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function\s*\(""",
            re.VERBOSE,
        ),
        re.compile(
            r"""(?:export\s+)?(?:default\s+)?
                (?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>""",
            re.VERBOSE,
        ),
        re.compile(
            r"""(?:export\s+)?(?:default\s+)?
                (?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?[\w.]+\s*=>""",
            re.VERBOSE,
        ),
        re.compile(
            r"""(\w+)\s*:\s*(?:async\s+)?function\s*\(""",
        ),
        re.compile(
            r"""(\w+)\s*\([^)]*\)\s*\{""",
        ),
        re.compile(
            r"""(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{""",
        ),
        re.compile(
            r"""static\s+(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{""",
        ),
    ]

    _CLASS_PATTERN = re.compile(r"""(?:export\s+)?(?:default\s+)?class\s+(\w+)""")
    _IMPORT_LINE = re.compile(
        r"""^\s*(?:import\s|import\{|from\s|require\s*\()"""
    )

    def __init__(self, branch_keywords: List[str]):
        self.branch_keywords = branch_keywords

    def _strip_comments_and_strings(self, source: str) -> str:
        result = []
        i = 0
        in_single_comment = False
        in_multi_comment = False
        in_string = False
        string_char = None

        while i < len(source):
            ch = source[i]

            if in_multi_comment:
                if ch == '*' and i + 1 < len(source) and source[i + 1] == '/':
                    in_multi_comment = False
                    result.append('  ')
                    i += 2
                    continue
                result.append(' ')
                i += 1
                continue

            if in_single_comment:
                if ch == '\n':
                    in_single_comment = False
                    result.append('\n')
                else:
                    result.append(' ')
                i += 1
                continue

            if in_string:
                if ch == '\\':
                    result.append(' ')
                    result.append(' ')
                    i += 2
                    continue
                if ch == string_char:
                    in_string = False
                result.append(' ')
                i += 1
                continue

            if ch == '/' and i + 1 < len(source):
                if source[i + 1] == '/':
                    in_single_comment = True
                    result.append('  ')
                    i += 2
                    continue
                if source[i + 1] == '*':
                    in_multi_comment = True
                    result.append('  ')
                    i += 2
                    continue

            if ch in ('"', "'", '`'):
                in_string = True
                string_char = ch
                result.append(' ')
                i += 1
                continue

            result.append(ch)
            i += 1

        return ''.join(result)

    def _find_functions(self, lines: List[str], clean_lines: List[str]) -> List[Dict[str, Any]]:
        functions: List[Dict[str, Any]] = []
        i = 0
        while i < len(clean_lines):
            line = clean_lines[i]
            stripped = line.strip()

            if self._IMPORT_LINE.match(stripped):
                i += 1
                continue

            if self._CLASS_PATTERN.search(line):
                i += 1
                continue

            match = None
            for pattern in self._FUNC_PATTERNS:
                match = pattern.search(line)
                if match:
                    break

            if match:
                name = match.group(1)
                if name in ('if', 'for', 'while', 'switch', 'catch', 'class', 'return', 'throw', 'new', 'typeof', 'delete', 'void', 'else', 'do'):
                    i += 1
                    continue

                end_idx = _BraceBalancer.find_block_end(clean_lines, i)
                functions.append({
                    "name": name,
                    "start": i + 1,
                    "end": end_idx + 1,
                })
                i = end_idx + 1
                continue

            i += 1

        return self._remove_nested_functions(functions)

    def _remove_nested_functions(self, functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not functions:
            return functions
        result = [functions[0]]
        for f in functions[1:]:
            outer = result[-1]
            if not (f["start"] >= outer["start"] and f["end"] <= outer["end"]):
                result.append(f)
        return result

    def _count_complexity(self, clean_lines: List[str], start: int, end: int) -> int:
        count = 0
        for i in range(start - 1, min(end, len(clean_lines))):
            line = clean_lines[i]
            stripped = line.strip()
            if not stripped:
                continue

            if_re = re.compile(r'\bif\b')
            count += len(if_re.findall(line))

            for_re = re.compile(r'\bfor\b')
            count += len(for_re.findall(line))

            while_re = re.compile(r'\bwhile\b')
            count += len(while_re.findall(line))

            case_re = re.compile(r'\bcase\b\s+')
            count += len(case_re.findall(line))

            catch_re = re.compile(r'\bcatch\b')
            count += len(catch_re.findall(line))

            elif_re = re.compile(r'\belif\b|\belse\s+if\b')
            count += len(elif_re.findall(line))

            and_count = line.count('&&')
            or_count = line.count('||')
            count += and_count + or_count

            ternary_re = re.compile(r'\?\s*[^.?]*\s*:')
            ternary_matches = ternary_re.findall(line)
            for m in ternary_matches:
                if not re.match(r'\?\s*\.', m):
                    count += 1

        return count

    def _find_imports(self, source: str) -> List[str]:
        imports = []
        for match in re.finditer(
            r"""(?:import\s+(?:\{[^}]*\}\s+from\s+)?|import\s+|require\s*\(\s*)['"]([^'"]+)['"]""",
            source,
        ):
            imports.append(match.group(1))
        for match in re.finditer(r"""from\s+['"]([^'"]+)['"]""", source):
            mod = match.group(1)
            if mod not in imports:
                imports.append(mod)
        return imports

    def analyze(self, source: str, file_path: str) -> FileMetrics:
        lines = source.splitlines()
        clean_source = self._strip_comments_and_strings(source)
        clean_lines = clean_source.splitlines()

        raw_funcs = self._find_functions(lines, clean_lines)
        imports = self._find_imports(source)

        functions: List[FunctionMetrics] = []
        for rf in raw_funcs:
            func_lines = rf["end"] - rf["start"] + 1
            complexity = 1 + self._count_complexity(clean_lines, rf["start"], rf["end"])
            functions.append(FunctionMetrics(
                name=rf["name"],
                complexity=complexity,
                start_line=rf["start"],
                end_line=rf["end"],
                lines=func_lines,
            ))

        return FileMetrics(
            path=file_path,
            language="javascript",
            total_lines=len(lines),
            functions=functions,
            coupling=len(set(imports)),
            imports=imports,
        )


class JavaAnalyzer:
    _CLASS_PATTERN = re.compile(
        r"""(?:public|private|protected)?\s*(?:abstract\s+|final\s+|static\s+)*
            class\s+(\w+)""",
        re.VERBOSE,
    )
    _METHOD_PATTERN = re.compile(
        r"""(?:
            (?P<modifiers>(?:public|private|protected|static|final|synchronized|abstract|native|strictfp|\s)*)
            (?:<[^>]+>\s+)?
            (?P<return_type>[\w<>\[\]?,\s]+?)
            \s+(?P<name>\w+)
            \s*\((?P<params>[^)]*)\)
            (?:\s*throws\s+[\w,\s]+)?
            \s*\{
        )""",
        re.VERBOSE,
    )
    _CONSTRUCTOR_PATTERN = re.compile(
        r"""(?:
            (?P<modifiers>(?:public|private|protected)\s+)?
            (?P<name>\w+)
            \s*\([^)]*\)
            (?:\s*throws\s+[\w,\s]+)?
            \s*\{
        )""",
        re.VERBOSE,
    )

    def __init__(self, branch_keywords: List[str]):
        self.branch_keywords = branch_keywords

    def _find_class_name(self, lines: List[str], up_to_line: int) -> str:
        for i in range(min(up_to_line, len(lines))):
            match = self._CLASS_PATTERN.search(lines[i])
            if match:
                return match.group(1)
        return ""

    def _find_methods(self, lines: List[str]) -> List[Dict[str, Any]]:
        methods: List[Dict[str, Any]] = []
        i = 0
        class_name = ""

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            class_match = self._CLASS_PATTERN.search(line)
            if class_match:
                class_name = class_match.group(1)
                i += 1
                continue

            if stripped.startswith("import ") or stripped.startswith("package "):
                i += 1
                continue

            if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                i += 1
                continue

            method_match = self._METHOD_PATTERN.search(line)
            if method_match:
                name = method_match.group("name")
                if name in ('if', 'for', 'while', 'switch', 'catch', 'class', 'return', 'throw', 'new'):
                    i += 1
                    continue

                end_idx = _BraceBalancer.find_block_end(lines, i)
                display_name = f"{class_name}.{name}" if class_name else name
                methods.append({
                    "name": display_name,
                    "start": i + 1,
                    "end": end_idx + 1,
                })
                i = end_idx + 1
                continue

            i += 1

        return methods

    def _count_complexity(self, lines: List[str], start: int, end: int) -> int:
        count = 0
        in_block_comment = False
        for i in range(start - 1, min(end, len(lines))):
            line = lines[i]
            stripped = line.strip()

            if in_block_comment:
                if '*/' in line:
                    in_block_comment = False
                    after = line.split('*/', 1)[1]
                    line = after
                    stripped = line.strip()
                else:
                    continue

            if '/*' in line:
                before = line.split('/*', 1)[0]
                if '*/' in line:
                    after = line.split('*/', 1)[1]
                    line = before + after
                    stripped = line.strip()
                else:
                    in_block_comment = True
                    line = before
                    stripped = line.strip()

            if stripped.startswith('//') or not stripped:
                continue

            if_re = re.compile(r'\bif\b')
            count += len(if_re.findall(line))

            for_re = re.compile(r'\bfor\b')
            count += len(for_re.findall(line))

            while_re = re.compile(r'\bwhile\b')
            count += len(while_re.findall(line))

            case_re = re.compile(r'\bcase\b\s+')
            count += len(case_re.findall(line))

            catch_re = re.compile(r'\bcatch\b')
            count += len(catch_re.findall(line))

            else_re = re.compile(r'\belse\b')
            count += len(else_re.findall(line))

            and_count = line.count('&&')
            or_count = line.count('||')
            count += and_count + or_count

            ternary_re = re.compile(r'\?\s*[^.?]*\s*:')
            for m in ternary_re.findall(line):
                if not re.match(r'\?\s*\.', m):
                    count += 1

        return count

    def _find_imports(self, source: str) -> List[str]:
        imports = []
        for match in re.finditer(r"import\s+([\w.*]+);", source):
            imports.append(match.group(1))
        return imports

    def analyze(self, source: str, file_path: str) -> FileMetrics:
        lines = source.splitlines()
        imports = self._find_imports(source)
        raw_methods = self._find_methods(lines)

        functions: List[FunctionMetrics] = []
        for rm in raw_methods:
            func_lines = rm["end"] - rm["start"] + 1
            complexity = 1 + self._count_complexity(lines, rm["start"], rm["end"])
            functions.append(FunctionMetrics(
                name=rm["name"],
                complexity=complexity,
                start_line=rm["start"],
                end_line=rm["end"],
                lines=func_lines,
            ))

        return FileMetrics(
            path=file_path,
            language="java",
            total_lines=len(lines),
            functions=functions,
            coupling=len(set(imports)),
            imports=imports,
        )


def get_analyzer(language: str, branch_keywords: List[str]):
    if language == "python":
        return PythonAnalyzer(branch_keywords)
    elif language == "javascript":
        return JavaScriptAnalyzer(branch_keywords)
    elif language == "java":
        return JavaAnalyzer(branch_keywords)
    else:
        return None


def analyze_file(file_path: Path, language: str, branch_keywords: List[str]) -> Optional[FileMetrics]:
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        analyzer = get_analyzer(language, branch_keywords)
        if analyzer is None:
            return None
        return analyzer.analyze(source, str(file_path))
    except (SyntaxError, UnicodeDecodeError, Exception):
        return None
