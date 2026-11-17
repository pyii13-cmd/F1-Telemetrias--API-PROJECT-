"""Open the offline dashboard with the system's default browser."""
from pathlib import Path
import webbrowser

if __name__ == "__main__":
    dashboard = Path(__file__).resolve().with_name("dashboard.html")
    if not dashboard.is_file():
        raise SystemExit("Falta dashboard.html. Executa python src/web_exporter.py.")
    print(dashboard)
    webbrowser.open(dashboard.as_uri())
