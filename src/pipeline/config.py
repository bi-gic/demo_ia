from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import os


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(ENV_PATH)


def get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)

    if value is None or value == "":
        raise ValueError(f"Falta configurar la variable {name} en .env")

    return value


PIPELINE_NAME = get_env("PIPELINE_NAME", "DEMO_ETL_CLIENTES")

INPUT_DIR = PROJECT_ROOT / get_env("PIPELINE_INPUT_DIR", "data/input")
INPUT_PATTERN = get_env("PIPELINE_INPUT_PATTERN", "clientes_*.csv")
PROCESSING_MODE = get_env("PIPELINE_PROCESSING_MODE", "latest")

APP_TIMEZONE = get_env("APP_TIMEZONE", "America/Lima")
APP_TZ = ZoneInfo(APP_TIMEZONE)

LOGS_DIR = PROJECT_ROOT / "logs"
ERROR_DIR = PROJECT_ROOT / "data" / "error"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

EXPECTED_COLUMNS = [
    "IdCliente",
    "Documento",
    "NombreCliente",
    "FechaGestion",
    "MontoDeuda",
    "Estado",
]


def now_lima() -> datetime:
    """
    Devuelve la fecha/hora actual en la zona horaria configurada.
    Se retorna sin tzinfo para insertarla limpiamente en SQL Server DATETIME2.
    """
    return datetime.now(APP_TZ).replace(tzinfo=None)


def get_connection_string() -> str:
    driver = get_env("PIPELINE_SQL_DRIVER", "ODBC Driver 18 for SQL Server")
    host = get_env("PIPELINE_SQL_HOST", "localhost")
    port = get_env("PIPELINE_SQL_PORT", "1433")
    database = get_env("PIPELINE_SQL_DATABASE", "DemoAutomatizacionIA")
    user = get_env("PIPELINE_SQL_USER")
    password = get_env("PIPELINE_SQL_PASSWORD")

    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={host},{port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
        "Connection Timeout=10;"
    )


def resolve_input_file() -> Path:
    """
    Selecciona dinámicamente el archivo de entrada según:
    - PIPELINE_INPUT_DIR
    - PIPELINE_INPUT_PATTERN
    - PIPELINE_PROCESSING_MODE

    Modos soportados:
    - latest: toma el archivo más reciente por fecha de modificación.
    - first: toma el primer archivo ordenado por nombre.
    """
    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    files = list(INPUT_DIR.glob(INPUT_PATTERN))

    if not files:
        raise FileNotFoundError(
            f"No se encontraron archivos en {INPUT_DIR} con patrón {INPUT_PATTERN}"
        )

    mode = PROCESSING_MODE.lower()

    if mode == "latest":
        return max(files, key=lambda file: file.stat().st_mtime)

    if mode == "first":
        return sorted(files)[0]

    raise ValueError(
        f"PIPELINE_PROCESSING_MODE inválido: {PROCESSING_MODE}. Usa latest o first."
    )