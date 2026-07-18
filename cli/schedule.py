"""
CLI — schedule commands.

Usage:
    agentcrew-mcn schedule start --topic-file topics.txt --platform juejin --interval 6
    agentcrew-mcn schedule stop
    agentcrew-mcn schedule status
"""

import time
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
def schedule_group():
    """定时调度相关命令"""


@schedule_group.command()
@click.option(
    "--topic-file", "-f", "topic_file", required=True, help="话题列表文件（每行一个话题）"
)
@click.option(
    "--platform", "-p", "platforms", required=True, multiple=True, help="目标平台（可多次指定）"
)
@click.option(
    "--style",
    "-s",
    default="technical",
    type=click.Choice(["technical", "casual", "thread", "promotional"]),
    help="写作风格",
)
@click.option(
    "--project-info", "-P", default=None, help="项目/产品描述（文本或文件路径，用于推广写作）"
)
@click.option("--interval", "-i", default=6.0, type=float, help="发布间隔（小时）")
@click.option("--dry-run", is_flag=True, help="预览模式，不实际发布")
@click.pass_context
def start(ctx, topic_file, platforms, style, project_info, interval, dry_run):
    """启动定时发布任务"""
    orchestrator = ctx.obj.get("orchestrator")
    if not orchestrator:
        console.print("[red]❌ Orchestrator 未初始化。请检查 config.yaml。[/red]")
        return

    # Read topics from file
    topic_path = Path(topic_file)
    if not topic_path.exists():
        console.print(f"[red]❌ 话题文件不存在: {topic_file}[/red]")
        return

    topics = topic_path.read_text(encoding="utf-8").strip().split("\n")
    topics = [t.strip() for t in topics if t.strip()]
    if not topics:
        console.print("[red]❌ 话题文件为空[/red]")
        return

    # Resolve --project-info (load from file if it's a path to .md/.txt)
    resolved_project_info = ""
    if project_info:
        from pathlib import Path as _Path

        _pi_path = _Path(project_info)
        if _pi_path.exists() and _pi_path.suffix in (".md", ".txt"):
            resolved_project_info = _pi_path.read_text(encoding="utf-8")
        else:
            resolved_project_info = project_info

    console.print("\n[bold]📅  启动定时发布[/bold]")
    console.print(f"  [dim]话题数:[/dim] {len(topics)}")
    console.print(f"  [dim]目标平台:[/dim] {', '.join(platforms)}")
    console.print(f"  [dim]发布间隔:[/dim] 每 {interval} 小时")
    console.print(f"  [dim]模式:[/dim] {'预览' if dry_run else '实际发布'}")
    if resolved_project_info:
        console.print(f"  [dim]项目信息:[/dim] {len(resolved_project_info)} 字")
    console.print()

    # Set up scheduler
    from orchestrator.scheduler import Scheduler

    scheduler = Scheduler(
        min_interval_min=max(30, int(interval * 60)),
        jitter_min=30,
    )

    # Wire scheduler to orchestrator
    orchestrator.set_scheduler(scheduler)
    scheduler.set_callback(orchestrator.execute_pipeline)

    # Add one task per topic
    for topic in topics:
        task = orchestrator.create_task(
            task_type="write_and_publish",
            params={
                "topic": topic,
                "style": style,
                "platforms": list(platforms),
                "dry_run": dry_run,
                "project_info": resolved_project_info,
            },
        )
        scheduler.add_recurring_task(task, interval_minutes=interval * 60)

    console.print("[bold green]✅ 调度器已启动[/bold green]")
    console.print("[dim]按 Ctrl+C 停止[/dim]\n")

    # Show initial status
    status = scheduler.get_status()
    table = Table(title="调度计划")
    table.add_column("任务ID", style="cyan")
    table.add_column("下次执行时间")

    for task_id, next_run in status["next_runs"]:
        table.add_row(task_id, next_run.strftime("%Y-%m-%d %H:%M:%S"))
    console.print(table)

    try:
        # Run scheduler in background and show live status
        scheduler.start(block=False)
        try:
            while scheduler.is_running():
                time.sleep(5)
        except KeyboardInterrupt:
            console.print("\n[yellow]⏹  收到中断信号...[/yellow]")
        finally:
            scheduler.stop()
            console.print("[green]✅ 调度器已停止[/green]")
    except KeyboardInterrupt:
        scheduler.stop()
        console.print("\n[green]✅ 调度器已停止[/green]")


@schedule_group.command()
@click.pass_context
def stop(ctx):
    """停止所有定时任务"""
    orchestrator = ctx.obj.get("orchestrator")
    if not orchestrator:
        console.print("[red]❌ Orchestrator 未初始化[/red]")
        return

    scheduler = orchestrator._scheduler
    if not scheduler or not scheduler.is_running():
        console.print("[yellow]⚠️ 没有正在运行的调度器[/yellow]")
        return

    scheduler.stop()
    console.print("[green]✅ 调度器已停止[/green]")


@schedule_group.command()
@click.pass_context
def status(ctx):
    """查看调度状态和下次执行时间"""
    orchestrator = ctx.obj.get("orchestrator")
    if not orchestrator:
        console.print("[red]❌ Orchestrator 未初始化[/red]")
        return

    scheduler = orchestrator._scheduler
    if not scheduler:
        console.print("[yellow]⚠️ 调度器未配置[/yellow]")
        return

    status = scheduler.get_status()

    console.print("\n[bold]📊 调度器状态[/bold]")
    console.print(f"  运行中: {'✅ 是' if status['running'] else '❌ 否'}")

    table = Table(title="已调度任务")
    table.add_column("任务ID", style="cyan")
    table.add_column("下次执行时间")

    for task_id, next_run in status["next_runs"]:
        table.add_row(task_id, next_run.strftime("%Y-%m-%d %H:%M:%S"))

    console.print(table)

    # Show execution history
    history = orchestrator.get_history(limit=5)
    if history:
        hist_table = Table(title="最近执行记录")
        hist_table.add_column("时间", style="dim")
        hist_table.add_column("类型")
        hist_table.add_column("状态")
        hist_table.add_column("耗时")

        for h in reversed(history):
            hist_table.add_row(
                h.started_at.strftime("%H:%M:%S"),
                h.task_type,
                "✅" if h.success else "❌",
                f"{h.duration_seconds:.1f}s",
            )
        console.print(hist_table)
