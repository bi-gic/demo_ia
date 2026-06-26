# AGENTS.md

## Contexto del proyecto

Este repositorio corresponde a una demo de automatización IA para procesos ETL.

El flujo principal es:

```text
GitHub -> Jenkins -> Python ETL -> SQL Server Docker
```

El pipeline principal se ejecuta con:

```bash
python -m src.pipeline.main
```

El objetivo de la demo es mostrar un flujo de recuperación asistida por IA:

```text
Jenkins ejecuta pipeline
↓
El pipeline falla
↓
La IA analiza logs y código
↓
La IA propone una corrección
↓
La IA modifica código en una rama
↓
La IA agrega pruebas
↓
Se crea Pull Request
↓
Un humano aprueba
↓
Jenkins valida nuevamente
```

## Rol del agente IA

El agente debe actuar como asistente de recuperación de pipelines ETL.

Cuando un pipeline falle, debe:

1. Leer el error reportado por Jenkins.
2. Revisar el código relacionado.
3. Identificar la causa raíz.
4. Clasificar el tipo de problema.
5. Proponer una corrección mínima y segura.
6. Modificar el código solo si corresponde.
7. Agregar o actualizar pruebas unitarias.
8. Ejecutar pruebas.
9. Crear una rama Git.
10. Hacer commit.
11. Dejar el cambio listo para Pull Request.

## Tipos de errores posibles

El agente debe considerar que el error puede ser de distintos tipos:

* Error de estructura de archivo.
* Error de nombres de columnas.
* Error de tipo de dato.
* Error de validación de negocio.
* Error de transformación.
* Error de carga SQL.
* Error de conexión a base de datos.
* Error de dependencia Python.
* Error de configuración Jenkins.
* Error de lógica del pipeline.

El agente no debe asumir que todos los errores son de datos. Debe revisar la evidencia del log y el código antes de corregir.

## Reglas obligatorias

* No modificar `.env`.
* No escribir credenciales en código.
* No tocar passwords, tokens ni secretos.
* No hacer push directo a `main`.
* No hacer merge directo.
* No borrar logs.
* No borrar datos históricos.
* No modificar `docker-compose.yml` salvo que el error sea claramente de infraestructura.
* No modificar el `Jenkinsfile` salvo que el error esté claramente relacionado con CI/CD.
* No modificar tablas SQL salvo que el error sea claramente de modelo de datos.
* No reemplazar el pipeline completo si basta con una corrección puntual.
* No cambiar la arquitectura general del proyecto sin justificación.
* Mantener compatibilidad con el escenario exitoso actual.
* Toda corrección de código debe venir acompañada de una prueba.
* Si el error es de datos de entrada, primero debe validar si puede resolverse con una normalización segura.
* Si la solución puede ocultar datos malos, debe registrar una advertencia en logs.

## Archivos importantes

* `src/pipeline/main.py`: orquestador principal del ETL.
* `src/pipeline/config.py`: configuración, rutas y variables de entorno.
* `src/pipeline/validate.py`: validaciones de columnas y datos.
* `src/pipeline/transform.py`: transformación de datos.
* `src/pipeline/load.py`: carga en SQL Server.
* `src/pipeline/db.py`: conexión y registro de ejecuciones.
* `tests/`: pruebas unitarias.
* `Jenkinsfile`: pipeline CI/CD.
* `.env.example`: ejemplo de variables sin secretos.
* `.gitignore`: exclusiones de archivos sensibles o runtime.

## Flujo esperado de corrección

Cuando el agente detecte un error corregible en código, debe seguir este flujo:

```text
1. Confirmar causa raíz.
2. Crear una rama distinta de main.
3. Implementar corrección mínima.
4. Agregar o actualizar pruebas.
5. Ejecutar pytest.
6. Revisar git diff.
7. Hacer commit con mensaje claro.
8. Dejar listo para Pull Request.
```

## Criterio general de éxito

Una solución se considera correcta si:

1. Las pruebas unitarias pasan.
2. El escenario exitoso sigue funcionando.
3. El error reportado queda corregido.
4. No se exponen credenciales.
5. No se modifica `.env`.
6. No se hace push directo a `main`.
7. El cambio queda en una rama distinta de `main`.
8. El cambio es explicable en un Pull Request.

## Caso de demo actual

El escenario `DEMO_CASE = FALLA_COLUMNAS` falla porque el CSV viene con la columna:

```text
Fecha_Gestion
```

pero el pipeline espera:

```text
FechaGestion
```

El error observado en Jenkins fue:

```text
ValueError: Columnas obligatorias faltantes: FechaGestion
```

El error ocurre en:

```text
src/pipeline/main.py
src/pipeline/validate.py
```

La causa esperada es que el pipeline no tiene una normalización controlada de alias de columnas.

## Corrección esperada para el caso de demo

El agente debe corregir el pipeline para soportar alias controlados de columnas.

Alias requerido para este incidente:

```text
Fecha_Gestion -> FechaGestion
```

La solución debe permitir que el pipeline acepte archivos con:

```text
FechaGestion
```

y también archivos con:

```text
Fecha_Gestion
```

La corrección debe ser segura, explícita y cubierta por pruebas unitarias.

## Criterio de éxito del caso de demo

La solución del caso de demo se considera correcta si:

1. Las pruebas unitarias pasan.
2. El pipeline sigue funcionando con la columna original `FechaGestion`.
3. El pipeline también acepta el alias `Fecha_Gestion`.
4. El escenario `DEMO_CASE = EXITOSO` sigue pasando.
5. El escenario `DEMO_CASE = FALLA_COLUMNAS` pasa después del fix.
6. No se exponen credenciales.
7. No se modifica `.env`.
8. El cambio queda en una rama distinta de `main`.

## Rama sugerida para el caso de demo

```text
fix/normalizar-columnas-clientes
```

## Commit sugerido para el caso de demo

```text
Agregar normalizacion controlada de columnas de clientes
```

## Pull Request sugerido para el caso de demo

Título:

```text
Corregir fallo por alias de columna Fecha_Gestion
```

Descripción:

```text
Este cambio agrega normalización controlada de columnas para permitir que el pipeline procese archivos que envían Fecha_Gestion como alias de FechaGestion.

También se agregan pruebas unitarias para validar que el pipeline mantiene compatibilidad con la columna original y soporta el nuevo alias.
```
