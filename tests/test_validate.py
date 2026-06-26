import pandas as pd
import pytest

from src.pipeline.validate import normalize_column_aliases, validate_required_columns


# ---------------------------------------------------------------------------
# normalize_column_aliases
# ---------------------------------------------------------------------------

def _make_df(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame({col: [] for col in columns})


class TestNormalizeColumnAliases:
    def test_alias_fecha_gestion_se_renombra(self):
        df = _make_df(["IdCliente", "Documento", "NombreCliente", "Fecha_Gestion", "MontoDeuda", "Estado"])
        result = normalize_column_aliases(df)
        assert "FechaGestion" in result.columns
        assert "Fecha_Gestion" not in result.columns

    def test_columna_canonica_no_se_toca(self):
        df = _make_df(["IdCliente", "Documento", "NombreCliente", "FechaGestion", "MontoDeuda", "Estado"])
        result = normalize_column_aliases(df)
        assert "FechaGestion" in result.columns
        assert list(result.columns) == list(df.columns)

    def test_alias_no_se_aplica_si_canonica_ya_esta(self):
        """Si el archivo trae ambas columnas, no se sobreescribe la canónica."""
        df = _make_df(["IdCliente", "FechaGestion", "Fecha_Gestion"])
        result = normalize_column_aliases(df)
        assert "FechaGestion" in result.columns
        assert "Fecha_Gestion" in result.columns

    def test_columnas_sin_alias_no_se_modifican(self):
        df = _make_df(["IdCliente", "Documento", "MontoDeuda"])
        result = normalize_column_aliases(df)
        assert list(result.columns) == ["IdCliente", "Documento", "MontoDeuda"]

    def test_datos_se_preservan_al_renombrar(self):
        df = pd.DataFrame({
            "IdCliente": [1, 2],
            "Fecha_Gestion": ["2026-06-09", "2026-06-10"],
        })
        result = normalize_column_aliases(df)
        assert list(result["FechaGestion"]) == ["2026-06-09", "2026-06-10"]

    def test_emite_warning_al_renombrar(self, caplog):
        import logging
        df = _make_df(["Fecha_Gestion", "IdCliente"])
        with caplog.at_level(logging.WARNING):
            normalize_column_aliases(df)
        assert any("Fecha_Gestion" in msg for msg in caplog.messages)


# ---------------------------------------------------------------------------
# validate_required_columns — escenario EXITOSO y FALLA_COLUMNAS
# ---------------------------------------------------------------------------

COLUMNAS_CORRECTAS = ["IdCliente", "Documento", "NombreCliente", "FechaGestion", "MontoDeuda", "Estado"]
COLUMNAS_ALIAS = ["IdCliente", "Documento", "NombreCliente", "Fecha_Gestion", "MontoDeuda", "Estado"]


class TestValidateRequiredColumns:
    def test_escenario_exitoso_pasa(self):
        df = _make_df(COLUMNAS_CORRECTAS)
        validate_required_columns(df)  # no debe lanzar

    def test_escenario_falla_columnas_sin_normalizar_falla(self):
        """El archivo original con Fecha_Gestion falla si no se normaliza antes."""
        df = _make_df(COLUMNAS_ALIAS)
        with pytest.raises(ValueError, match="FechaGestion"):
            validate_required_columns(df)

    def test_escenario_falla_columnas_normalizado_pasa(self):
        """Después de normalize_column_aliases, el mismo archivo debe pasar validación."""
        df = _make_df(COLUMNAS_ALIAS)
        df_normalizado = normalize_column_aliases(df)
        validate_required_columns(df_normalizado)  # no debe lanzar

    def test_columna_faltante_genera_error_descriptivo(self):
        df = _make_df(["IdCliente", "Documento"])
        with pytest.raises(ValueError, match="Columnas obligatorias faltantes"):
            validate_required_columns(df)

    def test_multiples_columnas_faltantes_se_reportan(self):
        df = _make_df(["IdCliente"])
        with pytest.raises(ValueError) as exc_info:
            validate_required_columns(df)
        mensaje = str(exc_info.value)
        assert "Documento" in mensaje
        assert "FechaGestion" in mensaje
