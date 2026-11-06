# Pluvia SCZ — Sprint 1

Prototipo académico para explorar acumulación pluvial en una zona piloto de Santa Cruz de la Sierra. Configura lluvia, ejecuta un simulador simplificado, consulta mapas y recupera resultados guardados. **Experimental: no es un pronóstico ni una herramienta de alertas.**

Repositorio: https://github.com/Lole67/pluvia-scz

Proyecto académico anteriormente identificado como Flood Prediction System. La comparación formal de escenarios pertenece a los próximos hitos.

## Documentación

- [Manual completo funcional y técnico del Sprint 1](docs/SPRINT_1.md): instalación, uso, funciones, datos, cálculo, API, pruebas, limitaciones y lista de cierre.
- [Preparación y publicación en GitHub](docs/GITHUB.md).
- [Fuentes y condiciones de los datos](DATA_SOURCES.md).
- [Guion corto de demostración](GUIA_DEMOSTRACION.md).
- [Registro cronológico de avances](STATUS.md).

## Instalación desde un clon

Desde la carpeta que contiene `run.py`, en PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

Abrir http://127.0.0.1:5050 y mantener la terminal abierta. Detener con Ctrl+C.
Entorno comprobado: Python 3.12.14 en Windows. Se incluyen los datos preparados; no es necesario descargar FABDEM para esta demostración. Instalar dependencias requiere internet; el cálculo y la vista local funcionan sin red.

En el equipo original, el entorno está en la carpeta padre: usar `..\.venv\Scripts\python.exe run.py` o `INICIAR.cmd`. El iniciador actual requiere esa disposición; para un clon con entorno interno usar los comandos anteriores.

## Qué permite

- Configurar lluvia total, duración, humedad y drenaje hipotético.
- Mostrar terreno, índice relativo y agua máxima simulada sobre 576 celdas de 250 m.
- Consultar calles cuando haya conexión o usar una cuadrícula local sin internet.
- Ajustar transparencia y líneas, seleccionar celdas y consultar ayuda contextual.
- Recuperar ejecuciones guardadas en JSON.

## Estado y pruebas

Al 5/11/2026: recorrido principal implementado; 11 casos Python aprobados y pruebas JavaScript de presentación aprobadas. La superposición de datos sobre calles fue confirmada por el usuario. La revisión visual final y la comprobación en otro equipo siguen pendientes. El manual contiene la lista de aceptación; no se afirma validación frente a inundaciones reales.

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
node tests/test_presentation.cjs
```

Node solo se requiere para las pruebas JavaScript. `VALIDATION.json` y `SENSITIVITY.json` conservan evidencia del 3/11; no son observaciones reales. Las salidas son sensibles a conductancia y borde.

## Alcance y datos

Dominio de 36 km² con reporte central de 16 km². Elevación FABDEM agregada a 250 m; infiltración uniforme provisional; drenaje sintético y borde exterior cerrado. El índice es el máximo simulado en mm limitado a 100: **80 puntos no significan 80 % de probabilidad**.

SQLite, selección de polígonos, intervención local, comparación A/B y ML pertenecen a próximos hitos. Las calles son una referencia visual y no intervienen en el cálculo.

Los derivados FABDEM conservan las condiciones CC BY-NC-SA 4.0; ver `DATA_SOURCES.md`. No se ha elegido una licencia para el código propio. `.gitignore` excluye entornos, resultados personales, temporales y datos originales.
