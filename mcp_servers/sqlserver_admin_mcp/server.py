import os
import re
from pathlib import Path
from typing import Any

import pyodbc
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP


PROJECT_ROOT = Path(os.getenv("DEMO_PROJECT_ROOT", r"C:\proyectos\demo_automatizacion_ia"))
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(ENV_PATH)

mcp = FastMCP("SQL Server Admin Demo MCP")


def get_env_value(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise ValueError(f"Falta configurar {name} en el archivo .env")
    return value


def get_schema() -> str:
    schema = os.getenv("MCP_SQL_SCHEMA", "demo_ai")
    return validate_identifier(schema)


def get_connection() -> pyodbc.Connection:
    host = get_env_value("MSSQL_HOST", "localhost")
    port = get_env_value("MSSQL_PORT", "1433")
    database = get_env_value("MSSQL_DATABASE", "DemoAutomatizacionIA")
    user = get_env_value("MSSQL_USER")
    password = get_env_value("MSSQL_PASSWORD")
    driver = get_env_value("MSSQL_DRIVER", "ODBC Driver 18 for SQL Server")

    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={host},{port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
        "Connection Timeout=10;"
    )

    return pyodbc.connect(connection_string)


def validate_identifier(value: str) -> str:
    if not value:
        raise ValueError("Identificador vacío.")

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Identificador inválido: {value}")

    return value


def quote_identifier(value: str) -> str:
    safe = validate_identifier(value)
    return f"[{safe}]"


def table_ref(table_name: str, schema: str | None = None) -> str:
    safe_schema = quote_identifier(schema or get_schema())
    safe_table = quote_identifier(table_name)
    return f"{safe_schema}.{safe_table}"


def rows_to_dicts(cursor: pyodbc.Cursor, rows: list[Any]) -> list[dict[str, Any]]:
    if cursor.description is None:
        return []

    columns = [column[0] for column in cursor.description]
    result: list[dict[str, Any]] = []

    for row in rows:
        item = {}
        for index, column_name in enumerate(columns):
            value = row[index]
            item[column_name] = str(value) if value is not None else None
        result.append(item)

    return result


def normalize_sql_type(sql_type: str) -> str:
    value = sql_type.strip().upper()

    if ";" in value or "--" in value or "/*" in value or "*/" in value:
        raise ValueError(f"Tipo SQL inválido: {sql_type}")

    allowed_exact = {
        "INT",
        "BIGINT",
        "SMALLINT",
        "TINYINT",
        "BIT",
        "FLOAT",
        "REAL",
        "DATE",
        "DATETIME",
        "DATETIME2",
        "TIME",
        "MONEY",
    }

    if value in allowed_exact:
        return value

    varchar_match = re.fullmatch(r"(VAR)?CHAR\((MAX|[1-9][0-9]{0,3})\)", value)
    nvarchar_match = re.fullmatch(r"N(VAR)?CHAR\((MAX|[1-9][0-9]{0,3})\)", value)
    decimal_match = re.fullmatch(r"(DECIMAL|NUMERIC)\(([1-9][0-9]?),([0-9]|[1-9][0-9]?)\)", value)

    if varchar_match or nvarchar_match:
        return value

    if decimal_match:
        precision = int(decimal_match.group(2))
        scale = int(decimal_match.group(3))

        if precision > 38:
            raise ValueError("La precisión máxima permitida para DECIMAL/NUMERIC es 38.")

        if scale > precision:
            raise ValueError("La escala no puede ser mayor que la precisión.")

        return value

    raise ValueError(f"Tipo SQL no permitido: {sql_type}")


def clean_select_sql(query: str) -> str:
    cleaned = query.strip().rstrip(";")

    if not cleaned:
        raise ValueError("La consulta está vacía.")

    normalized = re.sub(r"\s+", " ", cleaned).lower()

    if not (normalized.startswith("select") or normalized.startswith("with")):
        raise ValueError("Solo se permiten consultas SELECT o WITH.")

    blocked_words = [
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "truncate",
        "merge",
        "exec",
        "execute",
        "create",
        "grant",
        "revoke",
        "deny",
        "backup",
        "restore",
        "xp_cmdshell",
        "sp_configure",
    ]

    for word in blocked_words:
        if re.search(rf"\b{word}\b", normalized):
            raise ValueError(f"Consulta bloqueada. Palabra no permitida: {word}")

    return cleaned


@mcp.tool()
def test_connection() -> dict[str, Any]:
    """
    Prueba la conexión a SQL Server y devuelve información básica.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                DB_NAME() AS database_name,
                USER_NAME() AS database_user,
                SUSER_SNAME() AS login_name,
                @@VERSION AS version
        """)
        row = cursor.fetchone()

    return {
        "status": "ok",
        "database": row[0],
        "database_user": row[1],
        "login_name": row[2],
        "version": row[3],
    }


@mcp.tool()
def list_tables(schema: str | None = None) -> list[dict[str, Any]]:
    """
    Lista tablas de la base de datos.
    Si no se indica schema, lista las tablas del schema configurado en MCP_SQL_SCHEMA.
    """
    target_schema = schema or get_schema()
    validate_identifier(target_schema)

    query = """
        SELECT 
            TABLE_SCHEMA AS schema_name,
            TABLE_NAME AS table_name
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
          AND TABLE_SCHEMA = ?
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    """

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, target_schema)
        rows = cursor.fetchall()

    return rows_to_dicts(cursor, rows)


@mcp.tool()
def describe_table(table_name: str, schema: str | None = None) -> list[dict[str, Any]]:
    """
    Describe columnas de una tabla.
    """
    target_schema = schema or get_schema()
    validate_identifier(table_name)
    validate_identifier(target_schema)

    query = """
        SELECT
            TABLE_SCHEMA AS schema_name,
            TABLE_NAME AS table_name,
            COLUMN_NAME AS column_name,
            DATA_TYPE AS data_type,
            IS_NULLABLE AS is_nullable,
            CHARACTER_MAXIMUM_LENGTH AS max_length,
            NUMERIC_PRECISION AS numeric_precision,
            NUMERIC_SCALE AS numeric_scale
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = ?
          AND TABLE_NAME = ?
        ORDER BY ORDINAL_POSITION
    """

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, target_schema, table_name)
        rows = cursor.fetchall()

    return rows_to_dicts(cursor, rows)


@mcp.tool()
def create_table(
    table_name: str,
    columns: list[dict[str, Any]],
    schema: str | None = None
) -> dict[str, Any]:
    """
    Crea una tabla en el schema demo_ai.

    Ejemplo de columns:
    [
      {"name": "IdCliente", "type": "INT", "nullable": false, "primary_key": true},
      {"name": "Documento", "type": "VARCHAR(20)", "nullable": false},
      {"name": "Nombre", "type": "VARCHAR(100)", "nullable": false},
      {"name": "Monto", "type": "DECIMAL(12,2)", "nullable": true}
    ]
    """
    target_schema = schema or get_schema()
    validate_identifier(table_name)
    validate_identifier(target_schema)

    if not columns:
        raise ValueError("Debes enviar al menos una columna.")

    column_definitions = []

    for column in columns:
        name = validate_identifier(str(column["name"]))
        sql_type = normalize_sql_type(str(column["type"]))

        nullable = bool(column.get("nullable", True))
        primary_key = bool(column.get("primary_key", False))
        identity = bool(column.get("identity", False))

        parts = [quote_identifier(name), sql_type]

        if identity:
            if sql_type not in {"INT", "BIGINT"}:
                raise ValueError("IDENTITY solo está permitido para INT o BIGINT.")
            parts.append("IDENTITY(1,1)")

        if primary_key:
            parts.append("NOT NULL PRIMARY KEY")
        else:
            parts.append("NULL" if nullable else "NOT NULL")

        column_definitions.append(" ".join(parts))

    full_table = table_ref(table_name, target_schema)
    columns_sql = ",\n            ".join(column_definitions)

    sql = f"""
        IF OBJECT_ID('{target_schema}.{table_name}', 'U') IS NULL
        BEGIN
            CREATE TABLE {full_table} (
                {columns_sql}
            )
        END
    """

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()

    return {
        "status": "ok",
        "message": f"Tabla {target_schema}.{table_name} creada o ya existente.",
        "schema": target_schema,
        "table": table_name,
        "columns": columns,
    }


@mcp.tool()
def insert_rows(
    table_name: str,
    rows: list[dict[str, Any]],
    schema: str | None = None
) -> dict[str, Any]:
    """
    Inserta registros en una tabla del schema demo_ai.
    """
    target_schema = schema or get_schema()
    validate_identifier(table_name)
    validate_identifier(target_schema)

    if not rows:
        raise ValueError("Debes enviar al menos un registro.")

    columns = list(rows[0].keys())

    if not columns:
        raise ValueError("El registro no contiene columnas.")

    for column in columns:
        validate_identifier(column)

    for row in rows:
        if set(row.keys()) != set(columns):
            raise ValueError("Todos los registros deben tener las mismas columnas.")

    full_table = table_ref(table_name, target_schema)
    column_sql = ", ".join(quote_identifier(column) for column in columns)
    placeholders = ", ".join("?" for _ in columns)

    sql = f"""
        INSERT INTO {full_table} ({column_sql})
        VALUES ({placeholders})
    """

    values = [
        tuple(row[column] for column in columns)
        for row in rows
    ]

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.fast_executemany = True
        cursor.executemany(sql, values)
        conn.commit()

    return {
        "status": "ok",
        "message": f"Registros insertados en {target_schema}.{table_name}.",
        "rows_inserted": len(rows),
    }


@mcp.tool()
def select_table(
    table_name: str,
    schema: str | None = None,
    max_rows: int = 100
) -> dict[str, Any]:
    """
    Consulta registros de una tabla del schema demo_ai.
    """
    target_schema = schema or get_schema()
    validate_identifier(table_name)
    validate_identifier(target_schema)

    if max_rows < 1:
        max_rows = 1

    max_allowed = int(os.getenv("MCP_SQL_MAX_ROWS", "500"))

    if max_rows > max_allowed:
        max_rows = max_allowed

    full_table = table_ref(table_name, target_schema)

    sql = f"""
        SELECT TOP ({max_rows}) *
        FROM {full_table}
    """

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()

    return {
        "status": "ok",
        "schema": target_schema,
        "table": table_name,
        "row_count": len(rows),
        "data": rows_to_dicts(cursor, rows),
    }


@mcp.tool()
def run_select_query(query: str, max_rows: int = 100) -> dict[str, Any]:
    """
    Ejecuta una consulta SELECT controlada.
    No permite INSERT, UPDATE, DELETE, DROP, ALTER ni EXEC.
    """
    cleaned = clean_select_sql(query)

    if max_rows < 1:
        max_rows = 1

    max_allowed = int(os.getenv("MCP_SQL_MAX_ROWS", "500"))

    if max_rows > max_allowed:
        max_rows = max_allowed

    wrapped_query = f"""
        SELECT TOP ({max_rows}) *
        FROM (
            {cleaned}
        ) AS q
    """

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(wrapped_query)
        rows = cursor.fetchall()

    return {
        "status": "ok",
        "row_count": len(rows),
        "data": rows_to_dicts(cursor, rows),
    }


@mcp.tool()
def update_rows_by_key(
    table_name: str,
    key_column: str,
    key_value: Any,
    set_values: dict[str, Any],
    schema: str | None = None,
    max_rows: int = 1
) -> dict[str, Any]:
    """
    Actualiza registros por una columna llave.
    Por seguridad, por defecto actualiza máximo 1 fila.
    """
    target_schema = schema or get_schema()
    validate_identifier(table_name)
    validate_identifier(target_schema)
    validate_identifier(key_column)

    if not set_values:
        raise ValueError("Debes enviar campos a actualizar.")

    if max_rows < 1:
        max_rows = 1

    if max_rows > 10:
        raise ValueError("Por seguridad, no se permite actualizar más de 10 filas por operación.")

    for column in set_values.keys():
        validate_identifier(column)

    full_table = table_ref(table_name, target_schema)

    set_sql = ", ".join(
        f"{quote_identifier(column)} = ?"
        for column in set_values.keys()
    )

    sql = f"""
        UPDATE TOP ({max_rows}) {full_table}
        SET {set_sql}
        WHERE {quote_identifier(key_column)} = ?
    """

    params = list(set_values.values()) + [key_value]

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        affected = cursor.rowcount
        conn.commit()

    return {
        "status": "ok",
        "message": f"Actualización ejecutada en {target_schema}.{table_name}.",
        "rows_affected": affected,
    }


@mcp.tool()
def delete_rows_by_key(
    table_name: str,
    key_column: str,
    key_value: Any,
    schema: str | None = None,
    max_rows: int = 1
) -> dict[str, Any]:
    """
    Elimina registros por una columna llave.
    Por seguridad, por defecto elimina máximo 1 fila.
    """
    target_schema = schema or get_schema()
    validate_identifier(table_name)
    validate_identifier(target_schema)
    validate_identifier(key_column)

    if max_rows < 1:
        max_rows = 1

    if max_rows > 10:
        raise ValueError("Por seguridad, no se permite eliminar más de 10 filas por operación.")

    full_table = table_ref(table_name, target_schema)

    sql = f"""
        DELETE TOP ({max_rows})
        FROM {full_table}
        WHERE {quote_identifier(key_column)} = ?
    """

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, key_value)
        affected = cursor.rowcount
        conn.commit()

    return {
        "status": "ok",
        "message": f"Eliminación ejecutada en {target_schema}.{table_name}.",
        "rows_affected": affected,
    }


if __name__ == "__main__":
    mcp.run()