import pandas as pd


def transform_clientes(df: pd.DataFrame) -> pd.DataFrame:
    transformed = df.copy()

    transformed["IdCliente"] = pd.to_numeric(
        transformed["IdCliente"],
        errors="coerce"
    ).astype("Int64")

    transformed["Documento"] = (
        transformed["Documento"]
        .astype(str)
        .str.strip()
    )

    transformed["NombreCliente"] = (
        transformed["NombreCliente"]
        .astype(str)
        .str.strip()
    )

    transformed["FechaGestion"] = pd.to_datetime(
        transformed["FechaGestion"],
        errors="coerce"
    ).dt.date

    transformed["MontoDeuda"] = pd.to_numeric(
        transformed["MontoDeuda"],
        errors="coerce"
    )

    transformed["Estado"] = (
        transformed["Estado"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    return transformed