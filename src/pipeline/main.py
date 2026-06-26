import logging
import shutil
from datetime import datetime

import pandas as pd

from src.pipeline.config import (
    PIPELINE_NAME,
    resolve_input_file,
    LOGS_DIR,
    ERROR_DIR,
    PROCESSED_DIR,
    now_lima,
)
from src.pipeline.db import (
    get_connection,
    start_execution,
    finish_execution,
    insert_rejected_rows,
)
from src.pipeline.validate import normalize_column_aliases, validate_required_columns, validate_rows
from src.pipeline.transform import transform_clientes
from src.pipeline.load import delete_existing_clientes, insert_clientes


class LimaFormatter(logging.Formatter):
    """
    Formatter personalizado para que los timestamps del log usen America/Lima.
    """

    def formatTime(self, record, datefmt=None):
        return now_lima().strftime(datefmt or "%Y-%m-%d %H:%M:%S")


def setup_logging() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    log_file = LOGS_DIR / f"pipeline_{now_lima().strftime('%Y%m%d_%H%M%S')}.log"

    formatter = LimaFormatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def save_rejected_report(rejected_rows: list[dict]) -> None:
    if not rejected_rows:
        return

    ERROR_DIR.mkdir(parents=True, exist_ok=True)

    output_file = ERROR_DIR / f"rechazados_{now_lima().strftime('%Y%m%d_%H%M%S')}.csv"

    pd.DataFrame(rejected_rows).to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig",
    )

    logging.info("Reporte de rechazados generado: %s", output_file)


def move_processed_file(input_file) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    destination = PROCESSED_DIR / input_file.name

    if destination.exists():
        timestamp = now_lima().strftime("%Y%m%d_%H%M%S")
        destination = PROCESSED_DIR / f"{input_file.stem}_{timestamp}{input_file.suffix}"

    shutil.move(str(input_file), str(destination))

    logging.info("Archivo movido a procesados: %s", destination)


def run_pipeline() -> None:
    setup_logging()

    logging.info("Iniciando pipeline: %s", PIPELINE_NAME)

    conn = None
    execution_id = None
    input_file = None

    registros_leidos = 0
    registros_cargados = 0
    registros_error = 0

    try:
        input_file = resolve_input_file()

        logging.info("Archivo de entrada seleccionado: %s", input_file)

        conn = get_connection()
        execution_id = start_execution(conn, PIPELINE_NAME)

        logging.info("Ejecución registrada con IdEjecucion=%s", execution_id)

        df = pd.read_csv(input_file)
        registros_leidos = len(df)

        logging.info("Registros leídos: %s", registros_leidos)

        df = normalize_column_aliases(df)

        validate_required_columns(df)

        transformed_df = transform_clientes(df)

        valid_df, rejected_rows = validate_rows(transformed_df)

        registros_error = len(rejected_rows)

        save_rejected_report(rejected_rows)

        insert_rejected_rows(
            conn=conn,
            archivo_origen=input_file.name,
            rejected_rows=rejected_rows,
        )

        delete_existing_clientes(conn, valid_df)

        registros_cargados = insert_clientes(conn, valid_df)

        estado = "EXITOSO" if registros_error == 0 else "EXITOSO_CON_RECHAZOS"

        finish_execution(
            conn=conn,
            execution_id=execution_id,
            estado=estado,
            registros_leidos=registros_leidos,
            registros_cargados=registros_cargados,
            registros_error=registros_error,
            mensaje_error=None,
        )

        move_processed_file(input_file)

        logging.info("Pipeline finalizado con estado: %s", estado)
        logging.info("Registros cargados: %s", registros_cargados)
        logging.info("Registros rechazados: %s", registros_error)

    except Exception as error:
        logging.exception("Error ejecutando pipeline")

        if conn is not None and execution_id is not None:
            finish_execution(
                conn=conn,
                execution_id=execution_id,
                estado="FALLIDO",
                registros_leidos=registros_leidos,
                registros_cargados=registros_cargados,
                registros_error=registros_error,
                mensaje_error=str(error),
            )

        raise

    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    run_pipeline()