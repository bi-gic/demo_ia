import logging

import pandas as pd

from src.pipeline.config import COLUMN_ALIASES, EXPECTED_COLUMNS


def normalize_column_aliases(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renombra columnas alias a sus nombres canónicos según COLUMN_ALIASES.
    Solo actúa cuando la columna alias está presente y la canónica no lo está,
    para no romper archivos que ya vienen correctamente formateados.
    """
    renames: dict[str, str] = {}

    for alias, canonical in COLUMN_ALIASES.items():
        if alias in df.columns and canonical not in df.columns:
            renames[alias] = canonical
            logging.warning(
                "Columna '%s' renombrada a '%s' por alias controlado. "
                "Verificar que el dato sea correcto.",
                alias,
                canonical,
            )

    return df.rename(columns=renames) if renames else df


def validate_required_columns(df: pd.DataFrame) -> None:
    missing_columns = [
        column for column in EXPECTED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Columnas obligatorias faltantes: "
            + ", ".join(missing_columns)
        )


def validate_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    valid_rows = []
    rejected_rows = []

    for index, row in df.iterrows():
        reasons = []

        if pd.isna(row.get("IdCliente")):
            reasons.append("IdCliente vacío")

        if pd.isna(row.get("Documento")) or str(row.get("Documento")).strip() == "":
            reasons.append("Documento vacío")

        if pd.isna(row.get("NombreCliente")) or str(row.get("NombreCliente")).strip() == "":
            reasons.append("NombreCliente vacío")

        if pd.isna(row.get("FechaGestion")):
            reasons.append("FechaGestion inválida o vacía")

        if pd.isna(row.get("MontoDeuda")):
            reasons.append("MontoDeuda inválido o vacío")

        if pd.isna(row.get("Estado")) or str(row.get("Estado")).strip() == "":
            reasons.append("Estado vacío")

        if reasons:
            rejected_rows.append({
                "Fila": int(index) + 2,
                "Motivo": "; ".join(reasons),
            })
        else:
            valid_rows.append(row)

    valid_df = pd.DataFrame(valid_rows)

    return valid_df, rejected_rows