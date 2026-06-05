import pandas as pd
import pyodbc

from src.pipeline.config import now_lima


def delete_existing_clientes(
    conn: pyodbc.Connection,
    df: pd.DataFrame,
) -> int:
    """
    Elimina registros existentes por IdCliente antes de insertar.
    Esto evita duplicados cuando se reprocesa información del mismo cliente.
    """
    if df.empty:
        return 0

    ids = [
        int(value)
        for value in df["IdCliente"].dropna().unique().tolist()
    ]

    if not ids:
        return 0

    sql = """
    DELETE FROM dbo.ClientesInput
    WHERE IdCliente = ?;
    """

    cursor = conn.cursor()
    values = [(item,) for item in ids]
    cursor.executemany(sql, values)
    conn.commit()

    return len(ids)


def insert_clientes(
    conn: pyodbc.Connection,
    df: pd.DataFrame,
) -> int:
    """
    Inserta registros válidos en dbo.ClientesInput.
    Inserta FechaCarga desde Python usando hora Perú/Lima,
    para no depender del SYSDATETIME() del contenedor Docker.
    """
    if df.empty:
        return 0

    sql = """
    INSERT INTO dbo.ClientesInput (
        IdCliente,
        Documento,
        NombreCliente,
        FechaGestion,
        MontoDeuda,
        Estado,
        FechaCarga
    )
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """

    fecha_carga = now_lima()
    values = []

    for _, row in df.iterrows():
        values.append((
            int(row["IdCliente"]),
            str(row["Documento"]),
            str(row["NombreCliente"]),
            row["FechaGestion"],
            float(row["MontoDeuda"]),
            str(row["Estado"]),
            fecha_carga,
        ))

    cursor = conn.cursor()
    cursor.fast_executemany = True
    cursor.executemany(sql, values)
    conn.commit()

    return len(values)