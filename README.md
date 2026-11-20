# Pluvia SCZ

Aplicación web local para configurar escenarios de lluvia, ejecutar simulaciones y consultar sus resultados sobre una zona piloto de Santa Cruz de la Sierra.

**Es un modelo experimental: no constituye un pronóstico ni un sistema de alertas.**

Repositorio: https://github.com/Lole67/pluvia-scz

La API y la interfaz se sirven desde ASP.NET Core. Python ejecuta el cálculo numérico sobre el terreno FABDEM preparado. SQLite almacena cuentas, escenarios y resultados; EF Core administra las migraciones.

## Instalación desde cero en Windows

Esta guía utiliza **Windows de 64 bits y PowerShell**. Ejecuta los comandos uno por uno. Si alguno falla, resuelve ese error antes de continuar.

El ZIP incluye el código y el terreno preparado. **No incluye Python, el SDK de .NET ni el entorno `.venv`**. La primera instalación necesita internet para descargar herramientas y dependencias. No necesitas ChatGPT, Codex, Visual Studio ni un servidor de base de datos para ejecutar el proyecto.

### 1. Extraer el proyecto y entrar en su carpeta

Haz clic derecho sobre el ZIP y selecciona **Extraer todo**. Abre PowerShell y entra en la carpeta que contiene `INICIAR.cmd`, `README.md`, `requirements.txt` y `run.py`.

Por ejemplo, si lo extrajiste en una carpeta llamada `Flood_Prediction_System` en el escritorio:

```powershell
cd (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Flood_Prediction_System\pluvia-scz')
```

Si elegiste otra ubicación, escribe `cd` seguido de esa ruta entre comillas. Escribir solamente la ruta intenta ejecutarla como un programa; no entra en la carpeta.

Comprueba que estás en la carpeta correcta:

```powershell
Get-Item .\INICIAR.cmd, .\requirements.txt, .\run.py, .\api\Pluvia.Api\Pluvia.Api.csproj
```

Deben aparecer los cuatro archivos. Si no aparecen, busca la carpeta interior del ZIP que los contiene.

### 2. Comprobar o instalar Python 3.12

Comprueba si Windows reconoce Python 3.12:

```powershell
py -3.12 --version
```

Si muestra **Python 3.12.x**, puedes pasar al paso 3. Si aparece `No suitable Python runtime found` o `py is not recognized`, instala Python antes de continuar.

**Instalación con el administrador oficial de Python:**

1. Abre [Python para Windows](https://www.python.org/downloads/windows/) y descarga **Python install manager**.
2. Abre el instalador y completa la instalación.
3. Cierra PowerShell, abre una terminal nueva y vuelve a entrar en la carpeta del proyecto con `cd`.
4. Instala la versión del proyecto:

```powershell
pymanager install 3.12
```

5. Comprueba el intérprete instalado:

```powershell
pymanager exec -V:3.12 --version
```

Debe mostrar **Python 3.12.x**. Instalar el administrador y descargar el intérprete son pasos distintos.

Si ya tienes WinGet, también puedes instalar el administrador con este comando, en lugar de descargarlo desde la web:

```powershell
winget install --id 9NQ7512CXL7T --exact --source msstore
```

Después abre una terminal nueva y ejecuta los comandos `pymanager install 3.12` y `pymanager exec -V:3.12 --version`.

El comando `pymanager` evita confundir el administrador actual con un lanzador antiguo llamado `py`. Si `pymanager` tampoco se reconoce después de instalarlo y abrir otra terminal, consulta la [configuración oficial de Python en Windows](https://docs.python.org/3/using/windows.html).

### 3. Comprobar o instalar el SDK de .NET 10

```powershell
dotnet --list-sdks
```

Debe aparecer una línea que empiece por **10.0.**. Tener únicamente el Runtime no permite compilar este proyecto.

Si falta, abre [Descargar .NET 10](https://dotnet.microsoft.com/download/dotnet/10.0), elige **SDK → Windows → x64** y completa la instalación. Después cierra y vuelve a abrir PowerShell.

Como alternativa, si tienes WinGet:

```powershell
winget install --id Microsoft.DotNet.SDK.10 --exact
```

Vuelve a ejecutar `dotnet --list-sdks` y confirma la versión 10.0 antes de seguir.

### 4. Crear el entorno Python del proyecto

Desde la carpeta que contiene `INICIAR.cmd`, utiliza **una** de estas opciones.

Si instalaste Python con el administrador del paso 2:

```powershell
pymanager exec -V:3.12 -m venv .venv
```

Si ya tenías Python 3.12 y comprobaste que `py -3.12 --version` funciona:

```powershell
py -3.12 -m venv .venv
```

Comprueba el resultado:

```powershell
.\.venv\Scripts\python.exe --version
```

Debe mostrar **Python 3.12.x**. Si el archivo no existe, la creación del entorno falló: no continúes con la instalación de paquetes.

No copies una carpeta `.venv` desde otra computadora o ubicación. Créala en la carpeta definitiva del proyecto. No hace falta activar el entorno ni modificar la política de ejecución de PowerShell: los comandos usan su intérprete directamente.

### 5. Instalar las dependencias y compilar

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Cuando termine sin errores, verifica las dependencias Python:

```powershell
.\.venv\Scripts\python.exe -m pip check
```

La respuesta esperada es `No broken requirements found.`

Restaura los paquetes de .NET y compila la API:

```powershell
dotnet restore api/Pluvia.Api
```

```powershell
dotnet build api/Pluvia.Api --no-restore
```

La compilación debe terminar correctamente. Un `dotnet restore` exitoso no crea el entorno Python ni instala sus dependencias: son preparaciones independientes.

### 6. Iniciar y crear la cuenta local

```powershell
.\INICIAR.cmd
```

En una instalación sin cuentas, la terminal solicita:

1. Usuario del administrador: entre 3 y 40 caracteres; letras, números, punto, guion o guion bajo.
2. Nombre.
3. Contraseña de 12 a 128 caracteres.
4. Repetición de la contraseña.

La contraseña no se muestra mientras escribes. Esta cuenta pertenece a **Pluvia**, no a Microsoft. No se distribuyen credenciales predeterminadas.

Cuando aparezca `Now listening on`, abre:

- Aplicación: http://127.0.0.1:5050/
- Swagger: http://127.0.0.1:5050/swagger

Mantén la terminal abierta. Para detener el servidor, pulsa **Ctrl+C**.

### Volver a iniciar otro día

La instalación se realiza una vez. En los siguientes usos, entra en la carpeta del proyecto y ejecuta:

```powershell
.\INICIAR.cmd
```

Si actualizas el código, instala las dependencias del archivo `requirements.txt` actualizado y vuelve a ejecutar `dotnet restore api/Pluvia.Api` antes de iniciar.

## Solución de errores de instalación

| Mensaje o situación | Causa y solución |
|---|---|
| La ruta de una carpeta “no se reconoce como comando” | Falta `cd` delante de la ruta. Consulta el paso 1. |
| `No suitable Python runtime found` | El lanzador no encuentra Python 3.12. Instálalo siguiendo el paso 2; después crea `.venv`. |
| `py` sigue fallando, pero `pymanager` funciona | Usa `pymanager exec -V:3.12 -m venv .venv`. Puede existir un lanzador `py` antiguo. |
| “No se encontró el entorno Python” | No existe un entorno válido en la copia del proyecto. Completa el paso 4. |
| `.\.venv\Scripts\python.exe` no se reconoce | No se creó el entorno o estás en otra carpeta. Comprueba los pasos 1 y 4. |
| `dotnet` no se reconoce o no aparece un SDK 10.0 | Instala el SDK de .NET 10 y abre una terminal nueva. |
| `ModuleNotFoundError` al simular | Instala `requirements.txt` con el Python de `.venv`, como indica el paso 5. |
| `pip` o NuGet no consiguen descargar paquetes | Revisa internet y el mensaje de descarga. No continúes hasta que la instalación termine correctamente. |
| La página no abre | La terminal debe seguir abierta y mostrar `Now listening on`. Revisa cualquier error anterior y usa `http://127.0.0.1:5050/`. |
| Puerto 5050 ocupado | Comprueba si ya tienes Pluvia abierta en otra terminal. Detén esa instancia con Ctrl+C antes de iniciar otra. |
| No aparecen cuentas o resultados anteriores | Comprueba la carpeta del proyecto y `$env:PLUVIA_DATA`: podrías estar utilizando otra base. |

Si compartes un error para recibir ayuda, copia el comando y su salida completa. No incluyas contraseñas ni tokens.


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

### Elegir otra carpeta para la base (opcional)

Detén el servidor. Desde la raíz del proyecto, estos comandos usan una base separada para pruebas:

```powershell
$env:PLUVIA_DATA = Join-Path (Get-Location) 'work/prueba-local'
.\INICIAR.cmd
```

Para volver a la base predeterminada, detén el servidor y ejecuta:

```powershell
Remove-Item Env:PLUVIA_DATA -ErrorAction SilentlyContinue
.\INICIAR.cmd
```

En ambos casos abre http://127.0.0.1:5050/. La variable definida con `$env:` solo afecta a esa sesión de PowerShell y a los procesos que inicie.

## Migraciones y datos de prueba

La conexión local es `Data Source=data/private/pluvia.sqlite3;Foreign Keys=True`. No requiere un servidor ni credenciales de base de datos. Por defecto no necesitas configurar `PLUVIA_DATA`. Es una variable de entorno opcional, no un archivo del ZIP; indica otra carpeta para guardar `pluvia.sqlite3`. Cambiarla selecciona otra base SQLite y no traslada los usuarios ni resultados existentes.

Las migraciones están en `api/Pluvia.Api/Data/Migrations/`, junto con el snapshot del modelo. El arranque aplica las migraciones pendientes. Para aplicarlas sin iniciar la web ni crear cuentas:

```powershell
.\.venv\Scripts\python.exe run.py --migrate-only
```

Una instalación anterior sin historial EF recibe un respaldo SQLite consistente en `data/private/backups/before-ef-*/` antes de adoptar la migración inicial. No se reemplazan usuarios, escenarios ni resultados. Para bases existentes, utiliza el iniciador anterior: incluye ese respaldo.

En una base nueva también puede utilizarse la herramienta de EF Core:

```powershell
dotnet tool install --global dotnet-ef --version 10.0.11
dotnet ef database update --project api/Pluvia.Api
```

Después de crear la cuenta inicial y arrancar el servidor, otra terminal permite cargar dos escenarios sintéticos. El script pide las credenciales, utiliza la API y cierra su sesión; no guarda la contraseña:

```powershell
.\.venv\Scripts\python.exe scripts/seed_demo.py
```

No se incluyen cuentas ni bases privadas en el repositorio. El motor usa los datos territoriales preparados incluidos en `data/pilot-v1/`.

## Organización

- `api/Pluvia.Api/Controllers/`: rutas HTTP y códigos de respuesta.
- `api/Pluvia.Api/DTOs/`: contratos de entrada y salida.
- `api/Pluvia.Api/Entities/`: entidades persistidas y relaciones.
- `api/Pluvia.Api/Data/`: contexto EF Core y migraciones SQLite.
- `SimulationService.cs`: escenarios, ejecuciones e historial mediante operaciones asíncronas de EF Core.
- `AccountsService.cs` y `Database.cs`: autenticación transaccional, respaldo e importación; estas operaciones mantienen SQL parametrizado.
- `web/`, `flood/static/`: interfaz; `flood/` y `scripts/engine_bridge.py`: motor numérico.

## Swagger

En `POST /api/auth/login`, pulsa **Try it out**, introduce tus credenciales y ejecuta. Copia el campo `token`, pulsa **Authorize** y pega solamente su valor. Después puedes crear escenarios, simular y consultar resultados; se aplican los mismos permisos que en la interfaz.

El CRUD de escenarios incluye GET de colección e individual, POST (201 con `Location`), PUT y DELETE (204). La consulta relacionada es `GET /api/scenarios/{id}/simulations`. Un escenario con ejecuciones devuelve 409 al intentar borrarlo, para conservar el historial. `POST /api/runs` acepta `scenario_id` y devuelve 400 cuando la referencia no existe o no es accesible.

El contrato completo está en `/swagger/v1/swagger.json`. Las pruebas desde Swagger escriben en la base de datos de la instalación.

## Documentación

- [Manual funcional y técnico](docs/PLUVIA_SCZ_SPRINT_1.md).
- [Manual en PDF](docs/PLUVIA_SCZ_SPRINT_1.pdf).
- [Casos de uso](docs/CASOS_DE_USO.md).
- [Fuentes y condiciones de los datos](DATA_SOURCES.md).

## Pruebas automatizadas (opcionales para usar la aplicación)

Estas comprobaciones son para desarrollo; no necesitas ejecutarlas para iniciar Pluvia. La prueba JavaScript requiere Node.js instalado.

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

## Paquete del proyecto

```powershell
.\.venv\Scripts\python.exe scripts/package_project.py
```

Genera `work/distribution/pluvia-scz.zip` con código, migraciones, datos territoriales preparados y documentación. Excluye `bin`, `obj`, `.vs`, entornos, credenciales locales y bases privadas.

## Interpretación

La malla tiene 576 celdas de 250 m; el dominio abarca 36 km² y el reporte central 16 km². El índice equivale al agua máxima simulada en milímetros, limitada a 100. **80 puntos no significan 80 % de probabilidad de inundación.** La infiltración y el drenaje son supuestos uniformes; el borde es cerrado. Las calles son una referencia visual y no participan en el cálculo.

Los derivados FABDEM conservan las condiciones CC BY-NC-SA 4.0. Consulta `DATA_SOURCES.md`.

## Referencias de instalación

- [Administrador oficial de Python para Windows](https://docs.python.org/3/using/windows.html).
- [Descargas de Python para Windows](https://www.python.org/downloads/windows/).
- [SDK .NET 10](https://dotnet.microsoft.com/download/dotnet/10.0).
- [Instalación oficial de .NET en Windows](https://learn.microsoft.com/dotnet/core/install/windows).
