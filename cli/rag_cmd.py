"""
CLI — RAG knowledge base commands.

Usage:
    agentcrew-mcn rag ingest --file article.md --source "my_blog"
    agentcrew-mcn rag search --query "相关主题"
    agentcrew-mcn rag ingest-dir --dir docs/ --source "docs"
    agentcrew-mcn rag stats
"""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

# Maximum chunk size for RAG ingestion (characters)
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks for RAG ingestion."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start = end - overlap

    return chunks


@click.group()
def rag_group():
    """知识库（RAG）管理命令"""


@rag_group.command()
@click.option("--file", "-f", "file_path", required=True, help="要摄入的文本文件")
@click.option("--source", "-s", default="manual", help="内容来源标签")
@click.pass_context
def ingest(ctx, file_path, source):
    """将文档摄入知识库"""
    kb = ctx.obj.get("kb")
    if not kb:
        console.print("[red]❌ 知识库未初始化。请检查配置中 rag.enabled = true。[/red]")
        return

    path = Path(file_path)
    if not path.exists():
        console.print(f"[red]❌ 文件不存在: {file_path}[/red]")
        return

    with console.status("[bold blue]正在摄入文档...[/bold blue]", spinner="dots"):
        text = path.read_text(encoding="utf-8")
        chunks = _chunk_text(text)

        from rag.knowledge_base import Document

        documents = [
            Document(
                text=chunk,
                metadata={"source": source, "filename": path.name, "chunk": i},
                doc_id=f"{source}_{path.stem}_{i}",
            )
            for i, chunk in enumerate(chunks)
        ]

        kb.add_documents(documents)

    stats = kb.get_stats()
    console.print(f"\n[bold green]✅ 文档已摄入知识库[/bold green]")
    console.print(f"  [dim]来源:[/dim] {source}")
    console.print(f"  [dim]文件名:[/dim] {path.name}")
    console.print(f"  [dim]分块数:[/dim] {len(chunks)}")
    console.print(f"  [dim]知识库总数:[/dim] {stats['document_count']}")


@rag_group.command()
@click.option("--query", "-q", required=True, help="搜索查询")
@click.option("--limit", "-n", default=5, type=int, help="返回结果数量")
@click.pass_context
def search(ctx, query, limit):
    """在知识库中搜索相关内容"""
    kb = ctx.obj.get("kb")
    if not kb:
        console.print("[red]❌ 知识库未初始化[/red]")
        return

    from rag.retriever import Retriever

    retriever = Retriever(kb)

    with console.status("[bold blue]正在搜索知识库...[/bold blue]", spinner="dots"):
        results = retriever.retrieve_for_writing(query, limit=limit)

    if not results:
        console.print("[yellow]⚠️ 未找到相关内容[/yellow]")
        return

    console.print(f"\n[bold green]🔍 找到 {len(results)} 条相关结果[/bold green]\n")

    table = Table()
    table.add_column("#", style="dim")
    table.add_column("内容", style="white")
    table.add_column("相关度", style="cyan")
    table.add_column("来源", style="magenta")

    for i, r in enumerate(results, 1):
        score_str = f"{r.score:.2f}" if r.score else "N/A"
        source = r.metadata.get("source", "未知")
        # Show first 100 chars of each result
        preview = r.text[:100].replace("\n", " ") + ("..." if len(r.text) > 100 else "")
        table.add_row(str(i), preview, score_str, source)

    console.print(table)


@rag_group.command()
@click.option("--dir", "-d", "dir_path", required=True, help="文档目录路径")
@click.option("--source", "-s", default="docs", help="内容来源标签")
@click.pass_context
def ingest_dir(ctx, dir_path, source):
    """批量摄入整个目录的文档"""
    kb = ctx.obj.get("kb")
    if not kb:
        console.print("[red]❌ 知识库未初始化[/red]")
        return

    path = Path(dir_path)
    if not path.exists() or not path.is_dir():
        console.print(f"[red]❌ 目录不存在: {dir_path}[/red]")
        return

    # Collect all .md and .txt files in the directory
    files = list(path.rglob("*.md")) + list(path.rglob("*.txt"))
    if not files:
        console.print(f"[yellow]⚠️ 目录中未找到 .md 或 .txt 文件: {dir_path}[/yellow]")
        return

    from rag.knowledge_base import Document

    all_documents = []
    with console.status(f"[bold blue]正在批量摄入 {len(files)} 个文档...[/bold blue]", spinner="dots"):
        for f in files:
            text = f.read_text(encoding="utf-8", errors="ignore")
            chunks = _chunk_text(text)
            for i, chunk in enumerate(chunks):
                all_documents.append(
                    Document(
                        text=chunk,
                        metadata={"source": source, "filename": f.name, "path": str(f), "chunk": i},
                        doc_id=f"{source}_{f.stem}_{i}",
                    )
                )

        if all_documents:
            kb.add_documents(all_documents)

    stats = kb.get_stats()
    console.print(f"\n[bold green]✅ 批量摄入完成[/bold green]")
    console.print(f"  [dim]文件数:[/dim] {len(files)}")
    console.print(f"  [dim]总文档数:[/dim] {len(all_documents)}")
    console.print(f"  [dim]知识库总数:[/dim] {stats['document_count']}")


@rag_group.command()
@click.pass_context
def stats(ctx):
    """查看知识库统计信息"""
    kb = ctx.obj.get("kb")
    if not kb:
        console.print("[red]❌ 知识库未初始化[/red]")
        return

    stats = kb.get_stats()
    console.print(f"\n[bold]📊 知识库统计[/bold]\n")
    console.print(f"  库名: {stats['collection_name']}")
    console.print(f"  文档数: [bold cyan]{stats['document_count']}[/bold cyan]")
    console.print(f"  存储位置: {stats['persist_dir']}")
