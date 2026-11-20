# Pluvia SCZ

**Documentación funcional y técnica · Sprint 1**

## 1. Descripción

Pluvia SCZ permite explorar la acumulación de agua de lluvia en una zona piloto de Santa Cruz de la Sierra. El usuario configura lluvia, duración, humedad del suelo y drenaje hipotético. El sistema calcula la respuesta del terreno, representa los resultados en un mapa y conserva cada ejecución para consultarla posteriormente.

El modelo utiliza una malla de 24 × 24 celdas de 250 × 250 metros. Las 576 celdas forman un dominio de 36 km²; las 256 celdas centrales constituyen el área de reporte de 16 km². El margen exterior participa en el cálculo, aunque no forma parte de los indicadores del reporte.

Los resultados corresponden a un modelo simplificado. No constituyen mediciones de inundaciones reales, pronósticos ni alertas. La aplicación no determina la seguridad de calles o viviendas.

## 2. Acceso y permisos

El sistema utiliza cuentas locales. El administrador inicial se crea desde la terminal cuando la instalación no contiene cuentas. No se incluyen usuarios ni contraseñas predeterminados.

| Acción | Cliente | Administrador |
|---|---|---|
| Iniciar sesión y cambiar su contraseña | Sí | Sí |
| Simular y explorar el mapa | Sí | Sí |
| Guardar, recuperar y editar escenarios propios | Sí | Sí |
| Consultar resultados propios | Sí | Sí |
| Acceder a escenarios y resultados de otros usuarios | No | Sí |
| Consultar resultados importados sin propietario | No | Sí |
| Crear cuentas, asignar roles y cambiar su estado | No | Sí |
| Restablecer contraseñas de otras cuentas | No | Sí |

El servidor comprueba los permisos en cada petición. Los resultados ajenos no se muestran a un cliente, aunque conozca su identificador. Debe existir al menos un administrador activo.

Las contraseñas tienen entre 12 y 128 caracteres. Se almacenan mediante el generador de hashes de ASP.NET Core Identity. Las sesiones usan tokens aleatorios de 256 bits con una duración de ocho horas; SQLite conserva su hash SHA-256. El navegador guarda el token en `sessionStorage` y lo envía en `Authorization: Bearer`.

**Salir** revoca la sesión actual. Cambiar la contraseña, restablecerla, modificar el rol o desactivar la cuenta revoca sus sesiones. El inicio de sesión limita los intentos por dirección IP: diez intentos en quince minutos; un acceso correcto reinicia ese contador. El servidor escucha por defecto únicamente en `127.0.0.1`.

## 3. Casos de uso

Los dos casos principales representan las acciones del área de configuración y del área de resultados. La validación de parámetros forma parte de **Simular**; no se representa como una acción independiente del usuario. Ambos requieren una sesión activa.

### CU-01 · Simular

**Actores:** cliente y administrador.

**Objetivo:** obtener una representación de la respuesta del terreno ante un escenario.

1. El usuario ajusta los parámetros, elige un ejemplo o carga un escenario guardado.
2. Puede asignar un nombre y pulsar **Guardar escenario** para conservar los parámetros.
3. Pulsa **Simular**.
4. El servidor verifica los valores, registra la ejecución, solicita el cálculo y guarda el resultado.
5. La interfaz muestra la capa de índice relativo y los indicadores del reporte.

**Resultado:** ejecución guardada con identificador, propietario, fecha, parámetros y resultado. Si los parámetros no son válidos, el cálculo no comienza. Si el motor falla, la ejecución queda registrada con estado `failed` y se muestra un error; no se genera un resultado completo.

Guardar o editar parámetros no ejecuta el modelo. Al simular un escenario guardado sin modificaciones se mantiene su vínculo. Si se cambian los parámetros sin guardar, **Simular** crea un escenario separado con esos valores.

### CU-02 · Consultar resultados

**Actores:** cliente y administrador.

**Objetivo:** explorar un resultado actual o recuperar una ejecución anterior.

1. El usuario abre **Consultar resultados** y selecciona una ejecución, o explora la que acaba de calcular.
2. El servidor comprueba el acceso y recupera el resultado de SQLite.
3. El usuario cambia de capa, selecciona celdas, ajusta la cuadrícula o consulta los indicadores.

**Resultado:** visualización de los parámetros e indicadores originales sin repetir el cálculo. La lista contiene las últimas cien ejecuciones accesibles; las fallidas o en curso se indican mediante un aviso. Solo los resultados completos pueden cargarse en el mapa. Un resultado de otro territorio o con matrices incompatibles no reemplaza el mapa actual.

### Acciones de cuenta

| Acción visible | Uso |
|---|---|
| Iniciar sesión | Autenticar una cuenta local y acceder a la aplicación. |
| Mi cuenta / Cambiar contraseña | Cambiar la contraseña propia y cerrar las sesiones anteriores. |
| Usuarios / Crear usuario / Guardar | Administrar cuentas, roles, estado y restablecimiento de contraseñas. |
| Salir | Revocar la sesión actual y regresar al acceso. |

## 4. Funcionamiento de la interfaz

### Configuración

| Parámetro | Rango | Significado |
|---|---|---|
| Lluvia total | 0–300 mm | Agua aportada durante el evento; 1 mm equivale a 1 litro por m². |
| Duración de la lluvia | 0,1–24 horas | Tiempo durante el que se aplica la lluvia total. |
| Humedad inicial | 0–1 | Fracción que reduce la infiltración: seco 0, intermedio 0,5 y saturado 1. |
| Drenaje hipotético | 0–100 mm/h | Retirada uniforme de agua; no representa una medición de la red municipal. |

La intensidad mostrada es lluvia total dividida entre duración. Los ejemplos de 50 y 100 mm cargan una duración de dos horas, humedad 0,5 y drenaje de 5 mm/h. Es necesario pulsar **Simular** para ejecutarlos.

**Escenarios guardados** lista los últimos cien escenarios accesibles. Seleccionar **Nuevo escenario** y escribir un nombre permite guardar una configuración nueva. Seleccionar uno existente y pulsar **Guardar escenario** actualiza sus parámetros. Cada ejecución mantiene una copia independiente de los valores utilizados.

Durante el cálculo se bloquean los controles que pueden cambiar la configuración. Modificar parámetros después no modifica el resultado mostrado: aparece un aviso para distinguir la configuración actual de la última ejecución.

### Mapa

| Capa | Lectura |
|---|---|
| Altura del terreno | Elevación media FABDEM de cada celda, en metros. Más oscuro representa mayor altura. |
| Índice relativo | Agua máxima simulada en milímetros, limitada al intervalo 0–100. |
| Agua máxima simulada | Mayor acumulación de agua en cada celda durante el evento, en milímetros. |

La ficha de una celda muestra su ubicación en la malla, pertenencia al reporte, elevación, agua máxima e índice. Las líneas discontinuas delimitan el reporte central. **Mostrar cuadrícula** y **Opacidad** solo modifican la presentación.

**Mapa con calles** utiliza Leaflet y teselas de OpenStreetMap como referencia. **Vista sin internet** muestra la misma malla y permite seleccionar celdas sin descargar calles. **Centrar zona** ajusta la vista al dominio. Los fallos de la capa de calles no impiden el cálculo ni la consulta local.

### Indicadores e interpretación

El reporte muestra la mayor acumulación simulada, el índice medio y la superficie de cada categoría. Los intervalos del índice son: baja de 0 a menos de 25; media de 25 a menos de 50; alta de 50 a menos de 75; muy alta de 75 a 100.

Un índice de 80 no significa una probabilidad del 80 %. Una celda puede superar la lluvia local porque recibe agua de sus vecinas. Otras pueden acumular poco porque transfieren agua hacia celdas inferiores. Los máximos de distintas celdas no necesariamente ocurren al mismo tiempo.

El apartado de balance presenta lluvia, infiltración, drenaje, almacenamiento y residuo sobre el dominio completo. Comprueba la contabilidad del agua; no demuestra precisión frente a inundaciones observadas. **Ayuda** e **Interpretar** explican los parámetros y las capas.

## 5. Arquitectura y cálculo

| Componente | Responsabilidad |
|---|---|
| ASP.NET Core, en `api/Pluvia.Api/` | API, autenticación, roles, validación, escenarios, coordinación, resúmenes, historial y persistencia. Sirve también HTML, JavaScript y Swagger. |
| Interfaz, en `web/` y `flood/static/` | Formularios, sesión del navegador, mapa, selección de celdas y presentación de resultados. |
| Motor Python, en `flood/` | Cálculo numérico y lectura de las matrices territoriales. |
| SQLite | Usuarios, sesiones, escenarios, ejecuciones y resultados. |
| `data/pilot-v1/` | Territorio preparado: manifiesto, geometrías y matrices. |

La interfaz envía peticiones a una única API pública en .NET. El motor Python no publica rutas HTTP ni escribe el historial. .NET inicia el proceso `scripts/engine_bridge.py` y le entrega los parámetros mediante JSON por entrada estándar. Python devuelve las matrices y el balance por salida estándar. Se permiten dos procesos simultáneos y un máximo de tres minutos por proceso.

La simulación comienza sin agua superficial. En cada paso agrega lluvia uniforme, retira infiltración y drenaje sin producir almacenamiento negativo y transfiere agua entre las cuatro celdas vecinas según la altura del terreno más la lámina de agua. La infiltración base es 5 mm/h multiplicada por `1 - saturation`. El drenaje es uniforme y la conductancia provisional es 20 m²/s.

El paso nominal es de 30 segundos y se ajusta para cubrir exactamente la duración. El borde exterior es cerrado y el cálculo termina al cesar la lluvia, sin recesión posterior. El índice se calcula como `min(100, max(0, agua_maxima_mm))`.

El motor se identifica como `balance-d4-0.1.0` y el índice como `max-mm-linear-100-v1`. El resultado conserva esas versiones y la versión territorial para identificar el cálculo utilizado.

FABDEM V1-2 aporta la elevación, agregada desde aproximadamente 30 m a celdas de 250 m. Los decimales mostrados no implican precisión centimétrica ni validación topográfica local. El modelo no representa tuberías, obstáculos de calle, desbordamiento del Piraí ni observaciones reales. OpenStreetMap no interviene en el cálculo. Las fuentes y licencias están descritas en `DATA_SOURCES.md`.

## 6. Base de datos e historial

La base se crea en `data/private/pluvia.sqlite3` mediante las migraciones de EF Core 10.0.11, con claves foráneas, transacciones y modo WAL. El contexto `Data/PluviaDbContext.cs` se inyecta por petición; `SimulationService` usa consultas y escrituras asíncronas para escenarios, ejecuciones y resultados. La autenticación y la importación conservan SQL parametrizado. Los controladores HTTP, DTO, entidades y acceso a datos están separados en carpetas.

Las migraciones y el snapshot están en `api/Pluvia.Api/Data/Migrations/`. El arranque aplica las pendientes; `python run.py --migrate-only` las aplica sin abrir el servidor. Una base anterior sin historial EF se respalda en `data/private/backups/before-ef-*/` antes de adoptarla. Se conservan sus filas e identificadores.

| Tabla | Contenido y relación |
|---|---|
| `users` | Identificador, usuario único, nombre, hash de contraseña, rol y estado. |
| `sessions` | Hash del token, referencia a usuario y vencimiento. |
| `attempts` | Dirección IP y fecha de intentos de acceso. |
| `scenarios` | Nombre, propietario, parámetros JSON y fechas de creación y edición. |
| `simulations` | Identificador, escenario, propietario, fecha, copia de parámetros, estado y error. |
| `results` | Una fila por ejecución completada; contiene matrices, balance, resúmenes y metadatos en JSON. |
| `__EFMigrationsHistory` | Identificador y versión de las migraciones aplicadas. |
| `metadata` | Registro de importación y archivos omitidos. |

Un usuario puede tener varios escenarios y ejecuciones. Un escenario puede tener varias ejecuciones; cada ejecución tiene cero o un resultado. Los estados son `running`, `completed` y `failed`. Guardar el resultado y marcar la ejecución como completada forman una transacción. Al arrancar, las ejecuciones que quedaron en curso se marcan como fallidas por interrupción del servidor.

Los resultados conservan los parámetros originales incluso cuando se edita el escenario asociado. La API no ofrece edición ni eliminación de resultados. La consulta del historial no vuelve a ejecutar el motor. La API permite eliminar escenarios sin ejecuciones (204). Si un escenario tiene ejecuciones, su eliminación devuelve 409 para conservar la relación y el historial.

### Importación y respaldo

La primera inicialización importa las cuentas de `data/private/accounts.sqlite3` y los resultados compatibles de `data/runs/`. Se crea una copia en `data/private/backups/` y se conservan los originales. El registro en `metadata` evita repetir la importación. Los resultados sin un propietario reconocible quedan accesibles solo al administrador.

Los archivos incompletos o incompatibles se omiten; el administrador ve sus nombres en el aviso del historial. Corregir un original no lo reimporta automáticamente. Las contraseñas existentes se verifican con el formato anterior y se convierten al formato .NET tras un acceso correcto. Las sesiones anteriores no se importan.

Para respaldar la aplicación, detén el servidor y copia la carpeta completa `data/private/`, incluidos los archivos auxiliares de SQLite que existan. Los archivos de esa carpeta, sus respaldos, el entorno Python y los resultados personales están excluidos de Git.

## 7. API y Swagger

Swagger está disponible en `http://127.0.0.1:5050/swagger`. El documento OpenAPI está en `/swagger/v1/swagger.json`. Todas las operaciones de datos requieren sesión; el inicio de sesión es público. Las operaciones de usuarios requieren administrador.

| Método y ruta | Operación |
|---|---|
| `POST /api/auth/login` | Autenticar y obtener un token. |
| `GET /api/auth/me` | Consultar la cuenta autenticada. |
| `POST /api/auth/logout` | Revocar el token actual. |
| `POST /api/auth/password` | Cambiar la contraseña propia y revocar sesiones. |
| `GET /api/users` | Listar cuentas. |
| `POST /api/users` | Crear una cuenta. |
| `PUT /api/users/{id}` | Cambiar rol, estado o contraseña. |
| `GET /api/territory` | Consultar manifiesto territorial y geometrías. |
| `GET /api/scenarios` | Listar los últimos cien escenarios accesibles. |
| `POST /api/scenarios` | Guardar un escenario; devuelve 201 y `Location`. |
| `GET /api/scenarios/{id}` | Consultar un escenario por identificador. |
| `DELETE /api/scenarios/{id}` | Eliminar un escenario sin ejecuciones. |
| `GET /api/scenarios/{id}/simulations` | Consultar hasta cien ejecuciones relacionadas y accesibles. |
| `POST /api/runs` | Ejecutar un escenario referenciado mediante `scenario_id`. |
| `PUT /api/scenarios/{id}` | Editar un escenario accesible. |
| `POST /api/scenarios/{id}/simulate` | Simular los parámetros guardados. |
| `POST /api/simulate` | Crear y ejecutar un escenario con parámetros enviados. |
| `GET /api/runs` | Consultar las últimas cien ejecuciones accesibles. |
| `GET /api/runs/{id}` | Recuperar un resultado o el estado de una ejecución. |

`GET /api/runs?status=completed` filtra por estado. También se admiten `running` y `failed`. Con `include_warnings=1`, la respuesta contiene `runs` y `warnings`; los avisos de importación solo se entregan al administrador.

Los campos ausentes o inválidos devuelven 400. En `POST /api/runs`, una referencia `scenario_id` inexistente o inaccesible devuelve 400. Consultar un recurso inexistente o ajeno devuelve 404. La eliminación de un escenario con ejecuciones devuelve 409. Eliminar uno sin ejecuciones devuelve 204.

### Recorrido en Swagger

1. Abre `POST /api/auth/login`, pulsa **Try it out** e introduce tu usuario y contraseña en los campos `username` y `password`.
2. Pulsa **Execute**. Copia el valor de `token` de la respuesta.
3. Pulsa **Authorize**, pega el token sin escribir el prefijo Bearer y confirma.
4. Ejecuta `POST /api/scenarios` con este cuerpo:

```json
{
  "name": "Lluvia de 50 mm",
  "parameters": {
    "rain_mm": 50,
    "duration_h": 2,
    "saturation": 0.5,
    "drainage_mmh": 5
  }
}
```

5. Copia el `id` devuelto y úsalo en `POST /api/scenarios/{id}/simulate`.
6. Consulta `GET /api/runs` y recupera el resultado con `GET /api/runs/{id}`, utilizando el `run_id`.
7. Cambia el escenario con `PUT /api/scenarios/{id}`. Al consultar la ejecución anterior, sus parámetros siguen siendo los originales.

Para `POST /api/simulate`, envía directamente los cuatro parámetros, sin `name` ni el contenedor `parameters`. Todos son obligatorios y deben ser numéricos; no se aceptan campos adicionales.

Estas operaciones usan la misma base de datos que la interfaz. Un token de cliente no permite administrar usuarios ni acceder a resultados ajenos. Al cerrar sesión, el token deja de ser válido también en Swagger.

Las respuestas incluyen 201 para creación, 204 para operaciones sin cuerpo, 400 para entradas inválidas, 401 para falta de sesión, 403 para permisos insuficientes, 404 para registros inexistentes o ajenos, 409 para conflictos y 429 para exceso de intentos. Un error del motor se registra como ejecución fallida y produce un error 5xx.

## 8. Instalación y operación

Requisitos: SDK .NET 10 y Python 3.12. Desde la carpeta del proyecto:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
dotnet restore api/Pluvia.Api
.\INICIAR.cmd
```

En una instalación preparada, ejecuta únicamente `INICIAR.cmd`. El iniciador busca `.venv` dentro del proyecto y en la carpeta padre; `run.py` inicia .NET y selecciona ese intérprete para Python. En otros sistemas puede ejecutarse `python run.py` desde el entorno instalado.

Abre `http://127.0.0.1:5050/`. Si no hay cuentas, completa el registro del primer administrador en la terminal. Mantén la terminal abierta mientras usas la aplicación. Ctrl+C detiene el servidor. Solo debe ejecutarse una instancia por base de datos.

La instalación de paquetes requiere conexión. El terreno preparado está incluido y no requiere volver a descargar FABDEM. El cálculo y la vista local funcionan sin internet; las calles y la carga de Leaflet desde CDN requieren conexión si no hay una copia local de esa biblioteca.

### Recuperación de cuenta

Con acceso local al equipo y el servidor detenido:

```powershell
.\.venv\Scripts\python.exe scripts/reset_password.py
```

Introduce el usuario y una nueva contraseña. La cuenta queda activa y sus sesiones se revocan. Cuando el entorno Python está en la carpeta padre, sustituye `.\.venv` por `..\.venv`.

### Configuración del servidor

| Variable | Uso |
|---|---|
| `PLUVIA_ROOT` | Carpeta del proyecto; el iniciador la establece automáticamente. |
| `PLUVIA_PYTHON` | Intérprete usado por el proceso de cálculo. |
| `PLUVIA_DATA` | Directorio de la base privada; por defecto `data/private/`. |
| `PLUVIA_URL` | Dirección de escucha; por defecto `http://127.0.0.1:5050`. |

La configuración de fábrica está orientada al uso local. No deben publicarse cuentas, sesiones, resultados personales ni respaldos junto con el código.
