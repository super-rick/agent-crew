"""
CLI — write commands.

Usage:
    agentcrew-mcnwrite generate --topic "xxx" --style technical --platform juejin --rag
    agentcrew-mcnwrite free --prompt "请帮我写一篇关于..." --style casual
    agentcrew-mcnwrite outline --topic "xxx"
"""

from datetime import datetime

import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax

console = Console()


@click.group()
def write_group():
    """内容生成相关命令"""


@write_group.command()
@click.option("--topic", "-t", required=True, help="写作主题")
@click.option(
    "--style", "-s",
    default="technical",
    type=click.Choice(["technical", "casual", "thread", "promotional"]),
    help="写作风格",
)
@click.option("--platform", "-p", default="generic", help="目标平台")
@click.option("--skill", default="", help="使用的技能（trending_writing/technical_article/thread_writing）")
@click.option("--rag/--no-rag", default=True, help="是否使用 RAG 检索上下文")
@click.option("--project-info", "-P", default=None,
              help="项目/产品描述（文本或文件路径，用于推广写作）")
@click.option("--output", "-o", default=None, help="输出文件路径（默认打印到终端）")
@click.option("--dry-run", is_flag=True, help="预览模式：显示参数和提示词，不调用 LLM")
@click.pass_context
def generate(ctx, topic, style, platform, skill, rag, project_info, output, dry_run):
    """生成一篇内容（完整文章/帖子/Thread）"""
    orchestrator = ctx.obj.get("orchestrator")
    if not orchestrator:
        console.print("[red]❌ Orchestrator 未初始化。请检查 config.yaml。[/red]")
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

    # --- Dry-run mode: show params without calling LLM ---
    if dry_run:
        console.print(f"\n[bold yellow]🔍 Dry-Run 模式[/bold yellow]")
        console.print(f"  [dim]主题:[/dim] {topic}")
        console.print(f"  [dim]风格:[/dim] {style}")
        console.print(f"  [dim]平台:[/dim] {platform}")
        console.print(f"  [dim]RAG:[/dim] {'启用' if rag else '禁用'}")
        if skill:
            console.print(f"  [dim]技能:[/dim] {skill}")
        if output:
            console.print(f"  [dim]输出文件:[/dim] {output}")
        if resolved_project_info:
            console.print(f"  [dim]项目信息:[/dim] {len(resolved_project_info)} 字")
        console.print()

        console.print(Panel(
            f"将调用 Writer Agent 生成关于 [bold]'{topic}'[/bold] 的内容\n"
            f"风格: {style} | 平台: {platform} | RAG: {'启用' if rag else '禁用'}" +
            (f" | 技能: {skill}" if skill else "") +
            (f"\n项目信息: 已加载 ({len(resolved_project_info)} 字)" if resolved_project_info else ""),
            title="将创建的任务",
            border_style="yellow",
        ))
        console.print("[yellow]💡 去掉 --dry-run 以实际生成内容[/yellow]")
        return

    console.print(f"\n[bold]✍️  正在写作...[/bold]")
    console.print(f"  [dim]主题:[/dim] {topic}")
    console.print(f"  [dim]风格:[/dim] {style}")
    console.print(f"  [dim]平台:[/dim] {platform}")
    console.print(f"  [dim]RAG:[/dim] {'启用' if rag else '禁用'}")
    if skill:
        console.print(f"  [dim]技能:[/dim] {skill}")
    if resolved_project_info:
        console.print(f"  [dim]项目信息:[/dim] {len(resolved_project_info)} 字")
    console.print()

    with console.status("[bold blue]正在调用 AI 生成内容...[/bold blue]", spinner="dots"):
        task = orchestrator.create_task(
            task_type="write",
            params={
                "topic": topic,
                "style": style,
                "platform": platform,
                "skill": skill,
                "enable_rag": rag,
                "project_info": resolved_project_info,
            },
        )
        result = orchestrator.execute_pipeline(task)

    if not result.success:
        error = "Unknown error"
        if "writer" in result.results:
            error = result.results["writer"].error_message or error
        console.print(f"[red]❌ 生成失败: {error}[/red]")
        return

    writer_result = result.results.get("writer")
    if not writer_result or not writer_result.success:
        console.print("[red]❌ Writer Agent 执行失败[/red]")
        return

    data = writer_result.data
    content = data.get("formatted_content", data.get("raw_content", ""))

    # Display
    console.print("\n[bold green]✅ 内容生成完成[/bold green]\n")

    if platform in ("juejin", "zhihu", "generic"):
        md = Markdown(content)
        console.print(Panel(md, title="生成的内容", border_style="green"))
    else:
        console.print(Panel(content, title="生成的内容", border_style="green"))

    console.print(f"\n[dim]字数: {len(content)}[/dim]")
    console.print(f"[dim]耗时: {writer_result.duration_seconds:.1f}秒[/dim]")
    if data.get("rag_used"):
        console.print(f"[dim]RAG: 已使用[/dim]")
    if data.get("skill_used"):
        console.print(f"[dim]技能: {data['skill_used']}[/dim]")

    # Save to file if requested
    if output:
        filepath = output
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        console.print(f"\n[green]💾 已保存到: {filepath}[/green]")


@write_group.command()
@click.option("--prompt", "-p", required=True, help="自由格式写作提示")
@click.option("--style", "-s", default="casual", help="写作风格")
@click.pass_context
def free(ctx, prompt, style):
    """自由格式写作（不经过 Skill 编排，直接调用 LLM）"""
    writer = ctx.obj.get("writer")
    if not writer:
        console.print("[red]❌ Writer Agent 未初始化[/red]")
        return

    console.print(f"\n[bold]✍️  自由写作...[/bold]")
    console.print(f"  [dim]提示:[/dim] {prompt}")

    messages = writer._build_messages(prompt)
    with console.status("[bold blue]正在调用 AI...[/bold blue]", spinner="dots"):
        content = writer.llm_client.chat(messages)

    console.print("\n[bold green]✅ 生成完成[/bold green]\n")
    md = Markdown(content)
    console.print(Panel(md, title="生成的内容", border_style="green"))
    console.print(f"\n[dim]字数: {len(content)}[/dim]")


@write_group.command()
@click.option("--topic", "-t", required=True, help="话题")
@click.option("--style", "-s", default="technical", help="大纲风格")
@click.pass_context
def outline(ctx, topic, style):
    """为话题生成内容大纲"""
    writer = ctx.obj.get("writer")
    if not writer:
        console.print("[red]❌ Writer Agent 未初始化[/red]")
        return

    console.print(f"\n[bold]📋  生成大纲...[/bold]")
    console.print(f"  [dim]话题:[/dim] {topic}")

    with console.status("[bold blue]正在生成大纲...[/bold blue]", spinner="dots"):
        result = writer.generate_outline(topic, style)

    console.print("\n[bold green]✅ 大纲生成完成[/bold green]\n")
    console.print(Panel(result, title=f"「{topic}」内容大纲", border_style="blue"))
