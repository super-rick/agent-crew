"""
CLI — analyst commands.

Usage:
    agentcrew-mcn analyst analyze  --days 7 --platform juejin
    agentcrew-mcn analyst report    --days 7
    agentcrew-mcn analyst recommend --days 14
    agentcrew-mcn analyst history   --limit 20
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

console = Console()


@click.group()
def analyst_group():
    """内容效果分析与策略优化"""


@analyst_group.command()
@click.option("--days", "-d", default=7, help="统计最近多少天的数据")
@click.option("--platform", "-p", multiple=True, help="按平台过滤（可多次使用）")
@click.pass_context
def analyze(ctx, days, platform):
    """分析发布效果"""
    orchestrator = ctx.obj.get("orchestrator")
    if not orchestrator:
        console.print("[red]❌ Orchestrator 未初始化。请检查 config.yaml。[/red]")
        return

    params = {"action": "analyze", "days": days}
    if platform:
        params["platforms"] = list(platform)

    console.print("\n[bold]📊  正在分析发布效果...[/bold]")
    console.print(f"  [dim]统计周期:[/dim] 最近 {days} 天")
    if platform:
        console.print(f"  [dim]平台过滤:[/dim] {', '.join(platform)}")
    console.print()

    with console.status("[bold blue]正在计算指标...[/bold blue]", spinner="dots"):
        task = orchestrator.create_task(
            task_type="analyst",
            params=params,
        )
        result = orchestrator.execute_pipeline(task)

    if not result.success:
        error = "Unknown error"
        if "analyst" in result.results:
            error = result.results["analyst"].error_message or error
        console.print(f"[red]❌ 分析失败: {error}[/red]")
        return

    data = result.results["analyst"].data

    # Summary
    console.print("\n[bold green]✅ 分析完成[/bold green]\n")

    summary = Panel(
        f"[bold]总览[/bold]\n"
        f"  发布总数: {data['total_posts']} 篇\n"
        f"  ✅ 成功: {data['success_count']} 篇\n"
        f"  ❌ 失败: {data['fail_count']} 篇\n"
        f"  📈 成功率: {data['success_rate']}%",
        title="📊 效果分析概览",
        border_style="green",
    )
    console.print(summary)

    # Platform stats table
    if data.get("platform_stats"):
        table = Table(title="各平台表现", show_header=True, header_style="bold magenta")
        table.add_column("平台", style="cyan")
        table.add_column("总数", justify="right")
        table.add_column("成功", justify="right", style="green")
        table.add_column("失败", justify="right", style="red")
        table.add_column("成功率", justify="right")

        for ps in data["platform_stats"]:
            rate = ps["success_rate"]
            rate_style = "green" if rate >= 80 else "yellow" if rate >= 50 else "red"
            table.add_row(
                ps["platform"],
                str(ps["total"]),
                str(ps["success"]),
                str(ps["fail"]),
                f"[{rate_style}]{rate}%[/{rate_style}]",
            )
        console.print(table)

    # Error summary
    if data.get("error_summary"):
        console.print("\n[bold yellow]⚠️  错误类型统计[/bold yellow]")
        for err_type, count in data["error_summary"].items():
            console.print(f"  [{err_type}] x{count}")


@analyst_group.command()
@click.option("--days", "-d", default=7, help="统计最近多少天的数据")
@click.pass_context
def report(ctx, days):
    """生成效果分析报告"""
    orchestrator = ctx.obj.get("orchestrator")
    if not orchestrator:
        console.print("[red]❌ Orchestrator 未初始化。请检查 config.yaml。[/red]")
        return

    console.print(f"\n[bold]📝  正在生成效果报告...[/bold]")
    console.print(f"  [dim]统计周期:[/dim] 最近 {days} 天\n")

    with console.status("[bold blue]正在调用 AI 生成报告...[/bold blue]", spinner="dots"):
        task = orchestrator.create_task(
            task_type="analyst",
            params={"action": "report", "days": days},
        )
        result = orchestrator.execute_pipeline(task)

    if not result.success:
        error = "Unknown error"
        if "analyst" in result.results:
            error = result.results["analyst"].error_message or error
        console.print(f"[red]❌ 报告生成失败: {error}[/red]")
        return

    data = result.results["analyst"].data
    report_text = data.get("report", "")

    console.print("\n[bold green]✅ 报告生成完成[/bold green]\n")

    md = Markdown(report_text)
    console.print(Panel(md, title=f"📈 内容运营周报（最近 {days} 天）", border_style="blue"))


@analyst_group.command()
@click.option("--days", "-d", default=14, help="统计最近多少天的数据")
@click.pass_context
def recommend(ctx, days):
    """生成策略优化建议"""
    orchestrator = ctx.obj.get("orchestrator")
    if not orchestrator:
        console.print("[red]❌ Orchestrator 未初始化。请检查 config.yaml。[/red]")
        return

    console.print(f"\n[bold]💡  正在生成优化建议...[/bold]")
    console.print(f"  [dim]统计周期:[/dim] 最近 {days} 天\n")

    with console.status("[bold blue]正在调用 AI 分析...[/bold blue]", spinner="dots"):
        task = orchestrator.create_task(
            task_type="analyst",
            params={"action": "recommend", "days": days},
        )
        result = orchestrator.execute_pipeline(task)

    if not result.success:
        error = "Unknown error"
        if "analyst" in result.results:
            error = result.results["analyst"].error_message or error
        console.print(f"[red]❌ 建议生成失败: {error}[/red]")
        return

    data = result.results["analyst"].data
    recommend_text = data.get("recommendations", "")

    console.print("\n[bold green]✅ 优化建议生成完成[/bold green]\n")

    md = Markdown(recommend_text)
    console.print(Panel(md, title="💡 内容策略优化建议", border_style="yellow"))


@analyst_group.command()
@click.option("--limit", "-l", default=20, help="显示条数")
@click.pass_context
def history(ctx, limit):
    """查看发布历史记录"""
    publisher = ctx.obj.get("publisher")
    if not publisher:
        console.print("[red]❌ Publisher 未初始化[/red]")
        return

    console.print(f"\n[bold]📋  发布历史 (最近 {limit} 条)[/bold]\n")

    records = publisher.get_post_history(limit=limit)
    if not records:
        console.print("[yellow]暂无发布记录。[/yellow]")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("时间", style="dim")
    table.add_column("平台", style="cyan")
    table.add_column("状态")
    table.add_column("Post ID")
    table.add_column("错误信息")

    for r in reversed(records):
        status = "✅" if r.get("success") else "❌"
        table.add_row(
            r.get("posted_at", "?")[:16] if r.get("posted_at") else "?",
            r.get("platform", "?"),
            status,
            r.get("post_id", "-") or "-",
            r.get("error_message", "") or "",
        )

    console.print(table)
