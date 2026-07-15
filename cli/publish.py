"""
CLI — publish commands.

Usage:
    agent-crew publish post --text "xxx" --platform juejin
    agent-crew publish post --file article.md --platform juejin --platform zhihu
    agent-crew publish status --platform juejin
"""

from datetime import datetime

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


@click.group()
def publish_group():
    """内容发布相关命令"""


@publish_group.command()
@click.option("--text", "-t", default=None, help="要发布的文本内容")
@click.option("--file", "-f", "file_path", default=None, help="从文件读取内容")
@click.option("--platform", "-p", "platforms", required=True, multiple=True,
              help="目标平台（可多次指定，如 -p juejin -p zhihu）")
@click.option("--title", default=None, help="文章标题（掘金/知乎需要）")
@click.option("--dry-run", is_flag=True, help="预览模式，不实际发布")
@click.pass_context
def post(ctx, text, file_path, platforms, title, dry_run):
    """发布内容到指定平台"""
    publisher = ctx.obj.get("publisher")
    if not publisher:
        console.print("[red]❌ Publisher Agent 未初始化[/red]")
        return

    # Get content from text or file
    if not text and not file_path:
        console.print("[red]❌ 请通过 --text 或 --file 提供内容[/red]")
        return

    if file_path:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            console.print(f"[red]❌ 读取文件失败: {e}[/red]")
            return

    # Ensure we have text
    if not text or not text.strip():
        console.print("[red]❌ 内容不能为空[/red]")
        return

    # Check platform availability
    registered = publisher.list_platforms()
    for p in platforms:
        if p not in registered:
            available = ", ".join(registered) if registered else "(无已注册平台)"
            console.print(f"[red]❌ 平台 '{p}' 未注册。已注册: {available}[/red]")
            console.print("[yellow]💡 在 config.yaml 中配置平台信息后重新启动[/yellow]")
            return

    console.print(f"\n[bold]📤  准备发布...[/bold]")
    console.print(f"  [dim]目标平台:[/dim] {', '.join(platforms)}")
    console.print(f"  [dim]内容长度:[/dim] {len(text)} 字")
    if title:
        console.print(f"  [dim]标题:[/dim] {title}")
    if dry_run:
        console.print(f"  [dim]模式:[/dim] 预览 (dry-run)")
    console.print()

    content_preview = text[:200] + ("..." if len(text) > 200 else "")
    console.print(Panel(content_preview, title="内容预览", border_style="yellow"))

    if not dry_run:
        console.print()

    # Execute
    from agents.base import Task

    task = Task(
        task_id=f"cli_pub_{click.get_current_context().parent.parent.invoked_subcommand}_{datetime.now().timestamp()}",
        task_type="publish",
        params={
            "content": {
                "text": text,
                "title": title,
            },
            "platforms": list(platforms),
            "dry_run": dry_run,
        },
    )

    # We execute directly via publisher (not orchestrator) for simplicity
    with console.status("[bold blue]正在发布...[/bold blue]", spinner="dots"):
        result = publisher.execute(task)

    if not result.success:
        console.print(f"\n[red]❌ 发布完成（部分失败）[/red]")
    else:
        console.print(f"\n[bold green]✅ 发布完成[/bold green]")

    # Show results table
    table = Table(title="发布结果")
    table.add_column("平台", style="cyan")
    table.add_column("状态", style="bold")
    table.add_column("详情")

    for r in result.data.get("results", []):
        status_icon = "✅" if r["success"] else "❌"
        status_style = "green" if r["success"] else "red"
        detail = r.get("post_url") or r.get("error_message", "")
        table.add_row(
            r["platform"],
            f"[{status_style}]{status_icon} {'成功' if r['success'] else '失败'}[/{status_style}]",
            detail,
        )

    console.print(table)
    console.print(f"[dim]总耗时: {result.duration_seconds:.1f}秒[/dim]")


@publish_group.command()
@click.option("--platform", "-p", default=None, help="平台名称（留空显示所有）")
@click.pass_context
def status(ctx, platform):
    """查看各平台认证状态和速率限制"""
    publisher = ctx.obj.get("publisher")
    if not publisher:
        console.print("[red]❌ Publisher Agent 未初始化[/red]")
        return

    registered = publisher.list_platforms()
    if not registered:
        console.print("[yellow]⚠️ 没有已注册的平台。在 config.yaml 中配置平台信息。[/yellow]")
        return

    table = Table(title="平台状态")
    table.add_column("平台", style="cyan")
    table.add_column("认证状态", style="bold")
    table.add_column("日限额剩余")

    platforms_to_check = [platform] if platform else registered
    for p in platforms_to_check:
        if p not in registered:
            console.print(f"[red]❌ 平台 '{p}' 未注册[/red]")
            continue

        adapter = publisher.get_platform(p)
        ps = adapter.get_status()
        auth_status = "✅ 已认证" if ps.is_authenticated else "❌ 未认证"
        table.add_row(
            p,
            auth_status,
            str(ps.rate_limit_remaining) if ps.rate_limit_remaining else "N/A",
        )

    console.print(table)


@publish_group.command()
@click.pass_context
def history(ctx):
    """查看最近的发布历史"""
    publisher = ctx.obj.get("publisher")
    if not publisher:
        console.print("[red]❌ Publisher Agent 未初始化[/red]")
        return

    history_records = publisher.get_post_history(limit=20)
    if not history_records:
        console.print("[yellow]⚠️ 暂无发布历史[/yellow]")
        return

    table = Table(title="发布历史")
    table.add_column("时间", style="dim")
    table.add_column("平台", style="cyan")
    table.add_column("状态")
    table.add_column("链接")

    for r in reversed(history_records):
        table.add_row(
            r.get("posted_at", ""),
            r.get("platform", ""),
            "✅ 成功" if r.get("success") else "❌ 失败",
            r.get("post_url") or r.get("error_message", ""),
        )

    console.print(table)
