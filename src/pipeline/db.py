from typing import Any
import pyodbc

from src.pipeline.config import get_connection_string, now_lima


def get_connection() -> pyodbc.Connection:
    return pyodbc.connect(get_connection_string())


def start_execution(conn: pyodbc.Connection, pipeline_name: str) -> int:
    """
    Registra el inicio de ejecución del pipeline.
    Usa hora de aplicación configurada en APP_TIMEZONE.
    """
    sql = """
    INSERT INTO dbo.PipelineEjecuciones (
        NombrePipeline,
        Estado,
        RegistrosLeidos,
        RegistrosCargados,
        RegistrosError,
        MensajeError,
        FechaInicio,
        FechaFin
    )
    OUTPUT INSERTED.IdEjecucion
    VALUES (?, 'EN_PROCESO', 0, 0, 0, NULL, ?, NULL);
    """

    cursor = conn.cursor()
    cursor.execute(sql, pipeline_name, now_lima())
    execution_id = int(cursor.fetchone()[0])
    conn.commit()

    return execution_id


def finish_execution(
    conn: pyodbc.Connection,
    execution_id: int,
    estado: str,
    registros_leidos: int,
    registros_cargados: int,
    registros_error: int,
    mensaje_error: str | None = None,
) -> None:
    """
    Actualiza el estado final del pipeline.
    Usa hora de aplicación configurada en APP_TIMEZONE.
    """
    sql = """
    UPDATE dbo.PipelineEjecuciones
    SET
        Estado = ?,
        RegistrosLeidos = ?,
        RegistrosCargados = ?,
        RegistrosError = ?,
        MensajeError = ?,
        FechaFin = ?
    WHERE IdEjecucion = ?;
    """

    cursor = conn.cursor()
    cursor.execute(
        sql,
        estado,
        registros_leidos,
        registros_cargados,
        registros_error,
        mensaje_error,
        now_lima(),
        execution_id,
    )
    conn.commit()


def insert_rejected_rows(
    conn: pyodbc.Connection,
    archivo_origen: str,
    rejected_rows: list[dict[str, Any]],
) -> int:
    """
    Inserta filas rechazadas en dbo.ClientesRechazados.
    No usa el DEFAULT de SQL Server para evitar hora UTC del contenedor.
    """
    if not rejected_rows:
        return 0

    sql = """
    INSERT INTO dbo.ClientesRechazados (
        ArchivoOrigen,
        Fila,
        Motivo,
        FechaRegistro
    )
    VALUES (?, ?, ?, ?);
    """

    fecha_registro = now_lima()

    values = [
        (
            archivo_origen,
            item.get("Fila"),
            item.get("Motivo"),
            fecha_registro,
        )
        for item in rejected_rows
    ]

    cursor = conn.cursor()
    cursor.executemany(sql, values)
    conn.commit()

    return len(values)