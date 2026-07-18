"""
CLI — init command. Bootstraps AgentCrew configuration.

Usage:
    agentcrew-mcn init              # Create config in current directory
    agentcrew-mcn init --dir /opt   # Create config in specific directory
    agentcrew-mcn init --force      # Overwrite existing files without prompting
"""

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

console = Console()


@click.command()
@click.option(
    "--dir",
    "-d",
    "target_dir",
    default=".",
    help="Directory to create config files in (default: current directory)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing config.yaml and .env without prompting",
)
def init_command(target_dir, force):
    """Initialize AgentCrew: create config.yaml, .env, and directory structure."""
    target = Path(target_dir).resolve()

    # 1. Load templates from bundled package resources
    from importlib.resources import files as resource_files

    config_template = (
        resource_files("cli.templates").joinpath("config.example.yaml").read_text(encoding="utf-8")
    )
    env_template = (
        resource_files("cli.templates").joinpath("env.example").read_text(encoding="utf-8")
    )

    # 2. Determine target paths
    config_path = target / "config.yaml"
    env_path = target / ".env"
    data_chroma = target / "data" / "chroma"
    data_logs = target / "data" / "logs"

    # 3. Check for existing files and handle collision
    existing = []
    if config_path.exists():
        existing.append(str(config_path))
    if env_path.exists():
        existing.append(str(env_path))

    if existing and not force:
        console.print("[yellow]The following files already exist:[/yellow]")
        for fp in existing:
            console.print(f"  • {fp}")
        if not click.confirm("Overwrite them?"):
            console.print("[dim]Aborted.[/dim]")
            return

    # 4. Create directory structure
    data_chroma.mkdir(parents=True, exist_ok=True)
    data_logs.mkdir(parents=True, exist_ok=True)

    # 5. Write config.yaml
    config_path.write_text(config_template, encoding="utf-8")
    console.print(f"[green]✓[/green] Created: {config_path}")

    # 6. Write .env
    env_path.write_text(env_template, encoding="utf-8")
    console.print(f"[green]✓[/green] Created: {env_path}")

    # 7. Create .gitkeep files for empty data dirs
    (data_chroma / ".gitkeep").touch(exist_ok=True)
    (data_logs / ".gitkeep").touch(exist_ok=True)
    console.print(f"[green]✓[/green] Created: {data_chroma}/")
    console.print(f"[green]✓[/green] Created: {data_logs}/")

    # 8. Show next steps
    console.print()
    next_steps = Panel.fit(
        "\n".join(
            [
                "[bold]1.[/bold] Edit [cyan].env[/cyan] and add your API keys:",
                "   [dim]DEEPSEEK_API_KEY=sk-...[/dim]",
                "   [dim]JUEJIN_COOKIE=...[/dim]",
                "",
                "[bold]2.[/bold] Start generating content:",
                '   [dim]agentcrew-mcn write generate --topic "Your Topic" --style technical[/dim]',
                "",
                "[bold]3.[/bold] Explore all commands:",
                "   [dim]agentcrew-mcn--help[/dim]",
            ]
        ),
        title="[bold green]Next Steps[/bold green]",
        border_style="green",
    )
    console.print(next_steps)
