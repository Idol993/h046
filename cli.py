import sys
import os
import io
import multiprocessing
from pathlib import Path
from typing import List, Optional, Tuple

import click

from config import Config
from analyzer import analyze_file, FileMetrics
from scorer import Scorer, ProjectScore
from reporter import Reporter

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def _collect_files(
    scan_dir: Path, config: Config
) -> List[Tuple[Path, str, List[str]]]:
    all_extensions = config.get_all_extensions()
    ext_to_lang: dict = {}
    for lang, exts in all_extensions.items():
        for ext in exts:
            ext_to_lang[ext.lower()] = lang

    files_to_scan: List[Tuple[Path, str, List[str]]] = []
    scan_depth = config.get_scan_depth()

    for root, dirs, filenames in os.walk(scan_dir):
        rel_root = Path(root).relative_to(scan_dir)
        depth = len(rel_root.parts)
        if depth > scan_depth:
            dirs[:] = []
            continue

        for filename in filenames:
            file_path = Path(root) / filename
            suffix = file_path.suffix.lower()

            if suffix not in ext_to_lang:
                continue

            if config.is_ignored(file_path):
                continue

            language = ext_to_lang[suffix]
            branch_keywords = config.get_branch_keywords(language)
            files_to_scan.append((file_path, language, branch_keywords))

    return files_to_scan


def _worker(args: Tuple[Path, str, List[str]]) -> Optional[FileMetrics]:
    file_path, language, branch_keywords = args
    return analyze_file(file_path, language, branch_keywords)


def _scan_files(
    files_to_scan: List[Tuple[Path, str, List[str]]], num_workers: int
) -> List[FileMetrics]:
    results: List[FileMetrics] = []

    if num_workers <= 1 or len(files_to_scan) <= 1:
        with click.progressbar(files_to_scan, label="扫描文件") as bar:
            for args in bar:
                result = _worker(args)
                if result is not None:
                    results.append(result)
    else:
        with multiprocessing.Pool(processes=num_workers) as pool:
            with click.progressbar(
                pool.imap_unordered(_worker, files_to_scan),
                length=len(files_to_scan),
                label="扫描文件",
            ) as bar:
                for result in bar:
                    if result is not None:
                        results.append(result)

    return results


@click.group()
def cli():
    pass


@cli.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "html"], case_sensitive=False),
    default="html",
    help="报告格式 (json/html)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="输出文件路径",
)
@click.option(
    "--threshold",
    "-t",
    type=int,
    default=100,
    help="总扣分阈值，超过则退出码为 1",
)
@click.option(
    "--config",
    "-c",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="配置文件路径",
)
@click.option(
    "--workers",
    "-w",
    type=int,
    default=None,
    help="并行进程数 (默认: CPU核数 - 1)",
)
def scan(
    path: Path,
    output_format: str,
    output: Optional[Path],
    threshold: int,
    config_path: Optional[Path],
    workers: Optional[int],
):
    """扫描指定目录并生成技术债务报告"""
    scan_root = path.resolve()
    if config_path:
        project_root = config_path.resolve().parent
    else:
        project_root = Path.cwd()

    try:
        config = Config(config_path=config_path, project_root=project_root, scan_root=scan_root)
    except Exception as e:
        click.echo(f"❌ 加载配置失败: {e}", err=True)
        sys.exit(2)

    if output is None:
        ext = "json" if output_format.lower() == "json" else "html"
        output = Path.cwd() / f"report.{ext}"

    files_to_scan = _collect_files(scan_root, config)
    if not files_to_scan:
        click.echo("⚠️  未找到可扫描的代码文件")
        sys.exit(0)

    click.echo(f"🔍 找到 {len(files_to_scan)} 个待扫描文件")

    if workers is None:
        cpu_count = multiprocessing.cpu_count()
        num_workers = max(1, cpu_count - 1)
    else:
        num_workers = max(1, workers)

    click.echo(f"⚙️  使用 {num_workers} 个进程并行扫描")

    metrics_list = _scan_files(files_to_scan, num_workers)
    click.echo(f"✅ 成功分析 {len(metrics_list)} 个文件")

    scorer = Scorer(config)
    project_score: ProjectScore = scorer.score(metrics_list)

    click.echo("")
    click.echo("=" * 60)
    click.echo(f"📊 总扣分: {project_score.total_penalty}")
    click.echo(f"📁 扫描文件: {len(project_score.files)}")
    click.echo(f"🚨 违规文件: {len(project_score.files_with_violations)}")
    click.echo(f"📏 代码总行数: {project_score.total_lines}")
    click.echo(f"🎯 阈值: {threshold}")
    click.echo("=" * 60)

    if project_score.files_with_violations:
        click.echo("")
        click.echo("🚨 Top 违规文件 (按扣分排序):")
        top_violations = sorted(
            project_score.files_with_violations,
            key=lambda x: (-x.total_penalty, x.path),
        )[:10]
        for i, fs in enumerate(top_violations, 1):
            click.echo(
                f"  {i:2d}. [{fs.language}] {fs.path}  "
                f"(-{fs.total_penalty}分, {fs.total_lines}行)"
            )

    top_funcs = project_score.top_functions[:10]
    if top_funcs:
        click.echo("")
        click.echo("🔥 Top 违规函数 (按扣分排序):")
        for i, tf in enumerate(top_funcs, 1):
            loc = f"L{tf['start_line']}" if tf.get("start_line") else ""
            click.echo(
                f"  {i:2d}. [{tf['language']}] {tf['function_name']}  "
                f"({tf['metric']}={tf['value']}>{tf['threshold']}, "
                f"-{tf['penalty']}分)  {tf['file_path']}:{loc}"
            )

    reporter = Reporter(config)
    try:
        reporter.generate(project_score, output_format, output, threshold)
        click.echo("")
        click.echo(f"📄 报告已生成: {output.resolve()}")
    except Exception as e:
        click.echo(f"❌ 生成报告失败: {e}", err=True)
        sys.exit(3)

    if project_score.total_penalty > threshold:
        click.echo("")
        click.echo(f"❌ 总扣分 {project_score.total_penalty} 超过阈值 {threshold}，拦截！")
        sys.exit(1)
    else:
        click.echo("")
        click.echo(f"✅ 总扣分 {project_score.total_penalty} 在阈值 {threshold} 以内，通过！")
        sys.exit(0)


def main():
    cli()


if __name__ == "__main__":
    main()
