# Pluvia SCZ

Aplicación web local para explorar acumulación pluvial en una zona piloto de Santa Cruz de la Sierra. **Experimental: no es un pronóstico ni una herramienta de alertas.**

ASP.NET Core sirve la interfaz y la API, administra usuarios y escenarios, coordina simulaciones y guarda el historial en SQLite. Python ejecuta el cálculo numérico sobre el terreno FABDEM preparado.

## Instalación

Requisitos: **SDK .NET 10** y **Python 3.12**. Desde esta carpeta, en PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
dotnet restore api/Pluvia.Api
.\INICIAR.cmd
```

En una instalación preparada basta con `INICIAR.cmd`. También puede ejecutarse `python run.py` desde el entorno instalado. El iniciador busca Python en `.venv` dentro del proyecto y después en la carpeta padre. Mantén la terminal abierta y detén el servidor con Ctrl+C.

- Aplicación: http://127.0.0.1:5050/
- Swagger: http://127.0.0.1:5050/swagger

El primer arranque solicita crear un administrador en la terminal si no existen cuentas. No hay credenciales predeterminadas. La autenticación es propia de Pluvia; no utiliza una cuenta Microsoft.

El piloto preparado está incluido. La instalación de dependencias requiere internet; el cálculo y el mapa local no. El mapa de calles requiere conexión.

## Uso

1. Inicia sesión. El administrador crea cuentas desde **Usuarios**.
2. Ajusta lluvia, duración, humedad y drenaje. **Escenarios guardados** permite guardar y recuperar esos parámetros con un nombre.
3. Pulsa **Simular**. El resultado se guarda automáticamente.
4. Cambia la capa del mapa o selecciona una celda. En **Consultar resultados** recupera una ejecución sin recalcularla.

Cada cliente accede a sus escenarios y resultados. El administrador accede a todos. Cambiar un escenario no modifica sus ejecuciones anteriores.

## Datos locales

La base de datos está en `data/private/pluvia.sqlite3`. Guarda cuentas, sesiones, escenarios, ejecuciones y resultados. Las matrices se almacenan como JSON dentro de SQLite. Los archivos territoriales permanecen en `data/pilot-v1/`.

Cuando existen `data/private/accounts.sqlite3` y resultados en `data/runs/`, el primer arranque los importa una sola vez. Crea un respaldo en `data/private/backups/` y conserva los originales. Los archivos incompatibles se omiten y se indican al administrador. Las contraseñas existentes se conservan; es necesario volver a iniciar sesión.

Para respaldar la instalación, detén el servidor y copia toda la carpeta `data/private/`. No publiques esa carpeta: contiene datos de cuentas y resultados. Git excluye bases privadas, respaldos, entornos, compilaciones y ejecuciones personales.

## Swagger

En `POST /api/auth/login`, pulsa **Try it out**, introduce tus credenciales y ejecuta. Copia el campo `token`, pulsa **Authorize** y pega solamente su valor. Después puedes crear escenarios, simular y consultar resultados; se aplican los mismos permisos que en la interfaz.

El contrato completo está en `/swagger/v1/swagger.json`. Las pruebas desde Swagger escriben en la base de datos de la instalación.

## Documentación

- [Manual funcional y técnico](docs/PLUVIA_SCZ_SPRINT_1.md).
- [Manual en PDF](docs/PLUVIA_SCZ_SPRINT_1.pdf).
- [Casos de uso](docs/CASOS_DE_USO.md).
- [Fuentes y condiciones de los datos](DATA_SOURCES.md).

## Pruebas

```powershell
dotnet build api/Pluvia.Api.Tests
.\.venv\Scripts\python.exe -m pytest tests -q
node tests/test_presentation.cjs
```

Las pruebas crean bases temporales y verifican cálculo, permisos, sesiones, escenarios, persistencia e importación. Node solo se necesita para la prueba JavaScript. En un entorno que bloquea conexiones locales puede usarse el transporte en memoria del mismo servidor ASP.NET:

```powershell
$env:PLUVIA_TEST_TRANSPORT = 'memory'
.\.venv\Scripts\python.exe -m pytest tests -q
Remove-Item Env:PLUVIA_TEST_TRANSPORT
```

## Interpretación

La malla tiene 576 celdas de 250 m; el dominio abarca 36 km² y el reporte central 16 km². El índice equivale al agua máxima simulada en milímetros, limitada a 100. **80 puntos no significan 80 % de probabilidad de inundación.** La infiltración y el drenaje son supuestos uniformes; el borde es cerrado. Las calles son una referencia visual y no participan en el cálculo.

Los derivados FABDEM conservan las condiciones CC BY-NC-SA 4.0. Consulta `DATA_SOURCES.md`.
