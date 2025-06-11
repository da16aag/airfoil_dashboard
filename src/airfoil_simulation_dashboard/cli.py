"""Console script for airfoil_simulation_dashboard."""
import airfoil_simulation_dashboard

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.command()
def main():
    """Console script for airfoil_simulation_dashboard."""
    console.print("Replace this message by putting your code into "
               "airfoil_simulation_dashboard.cli.main")
    console.print("See Typer documentation at https://typer.tiangolo.com/")
    


if __name__ == "__main__":
    app()
