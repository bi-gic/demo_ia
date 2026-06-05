pipeline {
    agent any

    parameters {
        choice(
            name: 'DEMO_CASE',
            choices: ['EXITOSO', 'FALLA_COLUMNAS'],
            description: 'Selecciona el escenario de demo a ejecutar'
        )
    }

    environment {
        DEMO_PROJECT_ROOT = "${env.WORKSPACE}"
        JENKINS_VENV = '/var/jenkins_home/.venvs/demo_etl_clientes'

        PIPELINE_SQL_HOST = 'sqlserver'
        PIPELINE_SQL_PORT = '1433'
        PIPELINE_SQL_DATABASE = 'DemoAutomatizacionIA'
        PIPELINE_SQL_USER = 'pipeline_demo_user'
        PIPELINE_SQL_DRIVER = 'ODBC Driver 18 for SQL Server'

        PIPELINE_NAME = 'DEMO_ETL_CLIENTES'
        PIPELINE_INPUT_DIR = 'data/input'
        PIPELINE_INPUT_PATTERN = 'clientes_*.csv'
        PIPELINE_PROCESSING_MODE = 'latest'

        APP_TIMEZONE = 'America/Lima'
        PIP_DISABLE_PIP_VERSION_CHECK = '1'
    }

    stages {
        stage('Preparar archivo demo') {
            steps {
                dir("${env.DEMO_PROJECT_ROOT}") {
                    sh '''
                        set -e

                        echo "Preparando archivo de entrada para escenario: ${DEMO_CASE}"

                        mkdir -p data/input data/processed data/error logs reports

                        echo "Limpiando archivos temporales de entrada..."
                        rm -f data/input/clientes_*.csv

                        if [ "${DEMO_CASE}" = "EXITOSO" ]; then
                            echo "Creando archivo demo EXITOSO..."

                            cat > data/input/clientes_demo_exitoso.csv <<'CSV'
IdCliente,Documento,NombreCliente,FechaGestion,MontoDeuda,Estado
30,70000030,Cliente Demo Exitoso 01,2026-06-09,150.00,PENDIENTE
31,70000031,Cliente Demo Exitoso 02,2026-06-09,270.50,GESTIONADO
32,70000032,Cliente Demo Exitoso 03,2026-06-09,99.90,PENDIENTE
CSV

                        elif [ "${DEMO_CASE}" = "FALLA_COLUMNAS" ]; then
                            echo "Creando archivo demo con FALLA DE COLUMNAS..."

                            cat > data/input/clientes_demo_falla_columnas.csv <<'CSV'
IdCliente,Documento,NombreCliente,Fecha_Gestion,MontoDeuda,Estado
40,70000040,Cliente Demo Error 01,2026-06-09,180.00,PENDIENTE
41,70000041,Cliente Demo Error 02,2026-06-09,220.75,GESTIONADO
CSV

                        else
                            echo "DEMO_CASE no reconocido: ${DEMO_CASE}"
                            exit 1
                        fi

                        echo "Archivo generado:"
                        ls -la data/input
                    '''
                }
            }
        }

        stage('Validar workspace') {
            steps {
                dir("${env.DEMO_PROJECT_ROOT}") {
                    sh '''
                        set -e

                        echo "Ruta actual:"
                        pwd

                        echo "Contenido del proyecto:"
                        ls -la

                        echo "Contenido de data/input:"
                        ls -la data/input || true

                        echo "Contenido de data/processed:"
                        ls -la data/processed || true
                    '''
                }
            }
        }

        stage('Preparar entorno Python') {
            steps {
                dir("${env.DEMO_PROJECT_ROOT}") {
                    sh '''
                        set -e

                        echo "Validando entorno Python de Jenkins..."

                        if [ ! -f "$JENKINS_VENV/bin/python" ]; then
                            echo "Entorno no existe. Creando en: $JENKINS_VENV"
                            mkdir -p "$(dirname "$JENKINS_VENV")"
                            python3 -m venv "$JENKINS_VENV"
                        else
                            echo "Entorno Python ya existe: $JENKINS_VENV"
                        fi

                        . "$JENKINS_VENV/bin/activate"

                        CURRENT_HASH=$(sha256sum requirements.txt | awk '{print $1}')
                        SAVED_HASH=""

                        if [ -f "$JENKINS_VENV/.requirements_hash" ]; then
                            SAVED_HASH=$(cat "$JENKINS_VENV/.requirements_hash")
                        fi

                        echo "Validando imports principales..."

                        if python - <<'PY'
import pandas
import pyodbc
import dotenv
import pytest
print("Imports principales OK")
PY
                        then
                            IMPORTS_OK=1
                        else
                            IMPORTS_OK=0
                        fi

                        if [ "$CURRENT_HASH" = "$SAVED_HASH" ] && [ "$IMPORTS_OK" = "1" ]; then
                            echo "Dependencias ya instaladas y requirements.txt no cambio. Se omite pip install."
                        else
                            echo "Dependencias faltantes o requirements.txt cambio. Instalando..."
                            python -m pip install --upgrade pip
                            python -m pip install -r requirements.txt
                            echo "$CURRENT_HASH" > "$JENKINS_VENV/.requirements_hash"
                            echo "Dependencias instaladas correctamente."
                        fi
                    '''
                }
            }
        }

        stage('Validar driver ODBC') {
            steps {
                dir("${env.DEMO_PROJECT_ROOT}") {
                    sh '''
                        set -e

                        echo "Drivers ODBC disponibles:"
                        odbcinst -q -d
                    '''
                }
            }
        }

        stage('Validar conexion SQL') {
            steps {
                dir("${env.DEMO_PROJECT_ROOT}") {
                    withCredentials([
                        string(credentialsId: 'pipeline-sql-password', variable: 'PIPELINE_SQL_PASSWORD')
                    ]) {
                        sh '''
                            set -e

                            . "$JENKINS_VENV/bin/activate"

                            python - <<'PY'
import os
import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER={os.getenv('PIPELINE_SQL_HOST')},{os.getenv('PIPELINE_SQL_PORT')};"
    f"DATABASE={os.getenv('PIPELINE_SQL_DATABASE')};"
    f"UID={os.getenv('PIPELINE_SQL_USER')};"
    f"PWD={os.getenv('PIPELINE_SQL_PASSWORD')};"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
    "Connection Timeout=10;"
)

cursor = conn.cursor()
cursor.execute("SELECT DB_NAME() AS database_name")
print("Conexion OK a:", cursor.fetchone()[0])
conn.close()
PY
                        '''
                    }
                }
            }
        }

        stage('Ejecutar pipeline ETL') {
            steps {
                dir("${env.DEMO_PROJECT_ROOT}") {
                    withCredentials([
                        string(credentialsId: 'pipeline-sql-password', variable: 'PIPELINE_SQL_PASSWORD')
                    ]) {
                        sh '''
                            set -e

                            . "$JENKINS_VENV/bin/activate"
                            python -m src.pipeline.main
                        '''
                    }
                }
            }
        }
    }

    post {
        success {
            echo 'Pipeline Jenkins finalizado correctamente.'
        }

        failure {
            echo 'Pipeline Jenkins fallo. Revisar logs.'
        }

        always {
            dir("${env.DEMO_PROJECT_ROOT}") {
                archiveArtifacts artifacts: 'logs/*.log,data/error/*.csv', allowEmptyArchive: true
            }
        }
    }
}