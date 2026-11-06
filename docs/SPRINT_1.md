# Sprint 1 — Documentación funcional y técnica

**Pluvia SCZ · Santa Cruz de la Sierra**

Versión documental: 1.0 · Corte: 5 de noviembre de 2026 · Entrega prevista: 6 de noviembre.

## Contenido

1. [Objetivo y alcance](#1-objetivo-y-alcance)
2. [Instalación y arranque](#2-instalación-y-arranque)
3. [Manual de uso](#3-manual-de-uso)
4. [Cómo interpretar resultados](#4-cómo-interpretar-resultados)
5. [Datos y territorio](#5-datos-y-territorio)
6. [Funcionamiento del simulador](#6-funcionamiento-del-simulador)
7. [Arquitectura y archivos](#7-arquitectura-y-archivos)
8. [API y persistencia](#8-api-y-persistencia)
9. [Pruebas y evidencia](#9-pruebas-y-evidencia)
10. [Limitaciones y próximos hitos](#10-limitaciones-y-próximos-hitos)
11. [Problemas frecuentes](#11-problemas-frecuentes)
12. [Guion y cierre de entrega](#12-guion-y-cierre-de-entrega)

## 1. Objetivo y alcance

Aplicación web local para explorar cómo una lluvia hipotética podría acumularse sobre una zona piloto de Santa Cruz. Combina un modelo público de elevación con reglas simplificadas de infiltración, drenaje y movimiento del agua. El usuario configura condiciones, ejecuta el cálculo, consulta un mapa y recupera resultados guardados.

No pronostica cuándo lloverá, no observa inundaciones reales y todavía no emplea inteligencia artificial. El nombre del proyecto describe su objetivo general; la entrega de este sprint es un simulador exploratorio.

### Estado de entrega

El recorrido principal está implementado y tiene pruebas automáticas. El usuario confirmó que se muestra la cuadrícula sobre las calles. El acabado visual más reciente y el recorrido completo en un segundo equipo siguen pendientes de aceptación manual. Se puede presentar como **prototipo funcional del Sprint 1**, sin afirmar cierre de todas las verificaciones ni validación hidráulica.

| Función | Estado actual |
|---|---|
| Configurar lluvia, duración, humedad y drenaje | Implementada |
| Ejecutar balance y transferencias entre celdas | Implementada |
| Mostrar terreno, índice y agua máxima | Implementada |
| Calles, zoom y centrado | Implementados; requieren conexión para recursos externos |
| Vista local sin internet | Implementada con los datos preparados |
| Opacidad, líneas y ficha de celda | Implementadas; acabado visual pendiente de revisión final |
| Historial y recuperación tras reinicio | Implementados en JSON |
| Ayuda general y contextual | Implementada |
| SQLite, área libre, intervención, comparación A/B y ML | Pendientes de próximos hitos |

## 2. Instalación y arranque

### Requisitos

- Entorno comprobado: Windows y Python 3.12.14.
- Navegador moderno. Node.js solo es necesario para las pruebas JavaScript.
- Dependencias directas fijadas en `requirements.txt`; inventario del entorno en `dependencies.lock.txt`.
- Internet para instalar paquetes y mostrar calles. Una vez instalado, el cálculo y la vista local no requieren conexión.

### Instalación desde un clon o carpeta nueva

Abrir PowerShell **dentro de la carpeta del repositorio**, donde está `run.py`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

Abrir http://127.0.0.1:5050. Mantener la terminal abierta; detener con Ctrl+C. Esta forma de instalación no necesita activar el entorno ni modificar la política de ejecución de PowerShell.

El repositorio incluye los cuatro archivos preparados de `data/pilot-v1`. No hace falta descargar el archivo de elevación original para ejecutar la demostración. El historial de una instalación nueva estará vacío.

### Equipo original del proyecto

El entorno existente está **en la carpeta padre** de `flood-app`. Desde `flood-app`:

```powershell
..\.venv\Scripts\python.exe run.py
```

`INICIAR.cmd` y `start.ps1` actuales utilizan ese entorno de la carpeta padre. En un clon instalado con `.venv` dentro del repositorio, usar el comando de la instalación nueva; los iniciadores no detectan automáticamente esa disposición.

Después de cambios en plantillas, reiniciar el servidor y pulsar Ctrl+F5 en el navegador. El servidor escucha únicamente en `127.0.0.1:5050`, sin depurador; no está preparado como servicio público de producción.

## 3. Manual de uso

### 3.1 Preparar un escenario

El panel izquierdo contiene los grupos **Lluvia** y **Suelo y drenaje**. Los ejemplos de 50 y 100 mm cargan valores, pero no ejecutan automáticamente. Ambos usan 2 horas, humedad 0,5 y drenaje 5 mm/h.

| Campo | Significado | Valores admitidos |
|---|---|---|
| Lluvia total | Agua que cae durante todo el evento. 1 mm equivale a 1 litro por m² | 0 a 300 mm |
| Duración | Tiempo durante el cual cae esa lluvia | 0,1 a 24 h |
| Humedad inicial | Supuesto que reduce la infiltración; permanece constante | API: 0 a 1; interfaz: seco 0, intermedio 0,5, saturado 1 |
| Drenaje hipotético | Capacidad uniforme supuesta de retirar agua disponible | 0 a 100 mm/h |

La intensidad mostrada es lluvia dividida por duración: 50 mm en 2 horas equivalen a 25 mm/h. No es otra entrada independiente. La lluvia es constante en el tiempo y uniforme sobre el dominio.

### 3.2 Ejecutar

1. Elegir un ejemplo o modificar los campos.
2. Pulsar **Simular**. Los controles del escenario y el historial se bloquean mientras se calcula.
3. Esperar el mensaje de resultado guardado. El mapa pasa a mostrar el índice relativo.
4. Si se cambian entradas sin volver a ejecutar, un aviso indica que el mapa aún corresponde a la ejecución anterior.

Cada ejecución crea un archivo nuevo. Repetir los mismos parámetros puede producir los mismos valores, pero conserva identificadores distintos.

### 3.3 Explorar el mapa

- **Capa del mapa:** elegir terreno, índice o agua máxima. Las dos últimas requieren un resultado.
- **Mapa con calles:** carga Leaflet y el mapa base OpenStreetMap cuando hay conexión.
- **Vista sin internet:** muestra la misma cuadrícula y valores mediante SVG. No ofrece navegación de calles; las celdas se pueden seleccionar con ratón o teclado.
- **Centrar zona:** ajusta el mapa con calles a la extensión de la cuadrícula.
- **Opacidad:** modifica la transparencia de los colores, sin recalcular resultados.
- **Mostrar cuadrícula:** activa o desactiva las líneas internas. Los colores y la selección permanecen disponibles.
- En el mapa con calles, las líneas se hacen más discretas al alejarse.
- La leyenda flotante cambia según la capa. El terreno utiliza tonos tierra; las salidas simuladas, tonos azules.

El borde discontinuo delimita el área de reporte. El margen exterior se muestra atenuado, pero participa en el cálculo. No significa ausencia de datos.

### 3.4 Seleccionar una celda

Al pulsar una celda aparece una ficha con fila, columna, elevación media, agua máxima e índice. También indica si está dentro del reporte o en el margen de cálculo. Antes de simular, las salidas figuran como «Sin simular». **Cerrar** oculta la ficha y elimina la selección. Los controles visuales no cambian sus valores.

### 3.5 Consultar resultados e historial

El resumen muestra mayor acumulación del reporte, índice medio y superficie del reporte. La superficie es fija en este piloto: 16 km². Las categorías, la explicación del resultado y la comprobación del agua se consultan en apartados desplegables. El tiempo mostrado mide el cálculo del simulador, no toda la carga de la página.

Abrir **Resultados guardados** y elegir una ejecución. Se recuperan parámetros y matrices sin calcular de nuevo. El historial muestra las últimas 100 ejecuciones; los archivos anteriores no se eliminan por ese límite.

### 3.6 Ayuda

El botón superior **Ayuda** abre un panel lateral. Los botones «i» de los campos y **Interpretar** llevan al tema correspondiente. Incluye inicio, parámetros, mapa, fuentes y limitaciones. Se cierra mediante su botón o Escape. La simplificación general del lenguaje técnico queda pendiente de una revisión posterior con el usuario.

## 4. Cómo interpretar resultados

### Altura del terreno

Es la elevación promedio de una celda de 250 × 250 m. No es altura del agua. El piloto contiene elevaciones aproximadas entre 399,65 y 421,23 m. Mostrar decimales no significa que se tenga precisión centimétrica ni que cada calle del cuadro esté a esa misma altura.

### Agua máxima simulada

Es la mayor lámina equivalente calculada en cada celda durante el evento. Una celda puede recibir agua de vecinas y superar la lluvia local. Los máximos de distintas celdas pueden ocurrir en momentos diferentes: no representan necesariamente una fotografía simultánea.

### Índice relativo

`índice = limitar(acumulación máxima en mm, 0, 100)`

| Categoría | Intervalo del índice |
|---|---|
| Baja | 0 ≤ índice < 25 |
| Media | 25 ≤ índice < 50 |
| Alta | 50 ≤ índice < 75 |
| Muy alta | 75 ≤ índice ≤ 100 |

Es una escala provisional común, no un porcentaje de probabilidad. Un máximo de 40 mm produce índice 40; 100 y 300 mm producen ambos índice 100. Para distinguir valores superiores a 100 consultar agua máxima. En esa capa, el último color agrupa todos los valores desde 75 mm, sin limitar el dato numérico a 100.

### Ejemplo extremo y zonas claras

Con 300 mm en una hora, humedad 1 y drenaje 0, la infiltración y el drenaje no retiran agua. Sin embargo, el agua sigue pasando entre celdas. Las zonas que transfieren rápidamente a sus vecinas pueden acumular poco; las receptoras concentran más.

El cálculo usa 120 pasos de 30 segundos, con 2,5 mm añadidos por paso. Registra el máximo también antes del intercambio. En la ejecución revisada el índice estuvo entre 2,5 y 100, sin celdas con índice cero. El color claro y la transparencia del margen podían parecer ausencia de datos. Esto explica una salida del modelo, no certifica seguridad de una calle.

## 5. Datos y territorio

| Elemento | Implementación |
|---|---|
| Fuente de elevación | FABDEM V1-2, tesela S18W064 |
| Archivo original | `data/raw/S18W064_FABDEM_V1-2.tif`, 22.030.716 bytes; excluido de Git |
| Resolución de origen | Aproximadamente 30 m, 3600 × 3600 valores, EPSG:4326 |
| Preparación | Reproyección EPSG:32720 (UTM 20S), promedio a 250 m |
| Dominio | 24 × 24 celdas; 6 × 6 km; 36 km² |
| Reporte | 16 × 16 celdas centrales; 4 × 4 km; 16 km² |
| Margen | 1 km por lado; no validado como aislamiento hidrológico |
| Cobertura, SoilGrids, red de canales | No incorporados al cálculo actual |
| Infiltración | Base uniforme provisional de 5 mm/h |

Los cuatro archivos preparados son `territory.npz`, `cells.geojson`, `elevation_250m.tif` y `manifest.json`. El manifiesto identifica fuente, versión, límites y supuestos. La pendiente se calcula durante la preparación, pero el flujo actual usa directamente diferencias de elevación más agua.

SHA256 de la tesela original: `090104e063e4c4be897a836c7c835152a6c8fb3ce33acf1d9adf2d371603af2d`.

La regeneración requiere obtener esa tesela y ejecutar `scripts/prepare_territory.py`. El script verifica existencia y cobertura y genera el piloto; no descarga automáticamente el original. No reemplazar datos preparados de ejecuciones anteriores sin conservar su versión.

Fuente y condiciones de los datos: [DATA_SOURCES.md](../DATA_SOURCES.md).

## 6. Funcionamiento del simulador

Motor: `balance-d4-0.1.0`. Índice: `max-mm-linear-100-v1`.

En cada paso se realizan las siguientes operaciones:

1. Añadir la fracción de lluvia correspondiente.
2. Retirar infiltración: tasa efectiva = `5 × (1 − saturación)` mm/h, limitada al agua disponible.
3. Retirar drenaje, también limitado al agua restante.
4. Actualizar el máximo de cada celda.
5. Calcular diferencias de carga (elevación del suelo + lámina de agua) con sus cuatro vecinos: norte, sur, este y oeste.
6. Transferir agua usando una conductancia sintética de 20 m²/s y limitar conjuntamente las salidas para que el donante no entregue más de lo disponible.
7. Actualizar máximos y comprobar el balance del dominio.

El paso de la web es 30 segundos; se ajusta cuando es necesario para completar exactamente la duración. La función interna admite otras configuraciones para pruebas. El almacenamiento inicial de la web es cero. La ventana termina cuando cesa la lluvia: no se simula el vaciado posterior.

Balance: `almacenamiento inicial + lluvia − infiltración − drenaje = almacenamiento final`, dentro de tolerancia numérica. Los intercambios internos se cancelan al sumar el dominio. El borde exterior está cerrado: no permite entrada ni salida. El borde discontinuo del reporte no es una pared.

La tolerancia del balance es el mayor valor entre 10⁻⁶ m³ y 10⁻¹⁰ del volumen inicial más lluvia. La conservación numérica no demuestra exactitud física. El modelo no representa tuberías, desbordamientos del Piraí ni circulación detallada por calles.

## 7. Arquitectura y archivos

El navegador solicita datos mediante HTTP a Flask. Flask carga el territorio, valida entradas, ejecuta el simulador y guarda JSON. JavaScript dibuja los resultados. Todo funciona dentro de una aplicación local sencilla.

| Archivo o carpeta | Responsabilidad |
|---|---|
| `run.py` | Inicia Flask en localhost:5050 |
| `INICIAR.cmd`, `start.ps1` | Arranque con el entorno del equipo original |
| `flood/web.py` | Fábrica de aplicación, rutas HTTP, resumen y persistencia |
| `flood/simulator.py` | `Scenario`, validación, simulación e índice |
| `flood/territory.py` | Lectura y consistencia de matrices y geometrías |
| `flood/templates/index.html` | Estructura de la pantalla y ayuda |
| `flood/static/app.js` | Formulario, API, historial, SVG, Leaflet y controles |
| `flood/static/presentation.js` | Categorías, colores y compatibilidad de resultados |
| `flood/static/help.js` | Apertura, navegación y cierre de ayuda |
| `style.css`, `polish.css`, `compact.css`, `map-design.css` | Estilos acumulados, en ese orden |
| `scripts/prepare_territory.py` | Preparación del terreno a partir de FABDEM |
| `scripts/check_pilot.py` | Ejemplos, refinamiento temporal y evidencia |
| `scripts/review_sensitivity.py` | Sensibilidad a conductancia y margen |
| `tests/test_core.py` | Pruebas Python de cálculo y API |
| `tests/test_presentation.cjs` | Pruebas JavaScript de presentación |
| `data/pilot-v1/` | Datos preparados necesarios para ejecutar |
| `data/runs/` | Resultados generados; excluidos del repositorio |
| `VALIDATION.json`, `SENSITIVITY.json` | Evidencia numérica registrada el 3/11 |
| `STATUS.md` | Historial de avances y pendientes, con entradas cronológicas |

No hay implementaciones explícitas de Factory Method, Abstract Factory, Builder, Prototype o Singleton GoF. `create_app()` es una función fábrica; las copias de matrices y los objetos compartidos no se presentan como esos patrones. Tampoco hay ML ni base SQLite en esta entrega.

## 8. API y persistencia

| Método y ruta | Respuesta principal |
|---|---|
| `GET /` | Página HTML |
| `GET /api/territory` | Manifiesto, GeoJSON e indicador de Leaflet local |
| `POST /api/simulate` | Crea ejecución; 201 con resultado JSON; 400 por configuración inválida |
| `GET /api/runs` | Lista de las últimas 100 ejecuciones |
| `GET /api/runs/<run_id>` | Resultado guardado; 404 si no existe o el identificador es inválido |

Entrada de ejemplo:

```json
{"rain_mm":50,"duration_h":2,"saturation":0.5,"drainage_mmh":5}
```

Se rechazan campos desconocidos, valores ausentes, booleanos como números, valores no finitos y parámetros fuera de rango. El límite del cuerpo de petición es 4096 bytes.

El resultado incluye `run_id`, `scenario_id`, fecha UTC, parámetros, versiones, matrices `maximum_mm`, `final_mm`, `index`, balance temporal `ledger`, resumen del reporte, fuentes y advertencias. El navegador muestra fechas según su configuración local.

Cada ejecución usa un nombre único de fecha e identificador. Se escribe primero `.tmp` y se renombra al finalizar. No existe una API de edición ni borrado. Es inmutabilidad por el flujo de la aplicación, no protección contra edición manual de archivos.

La interfaz comprueba versión territorial, dimensiones y valores finitos antes de mostrar una ejecución. No hay comparación formal entre motores/versiones ni migración de resultados antiguos. No modificar manualmente un JSON para aparentar compatibilidad.

Para respaldar historial: detener el servidor y copiar `data/runs` junto con los datos territoriales, código y versiones correspondientes. Las ejecuciones se excluyen de Git para mantener separado el trabajo de cada usuario. No contiene cuentas ni autenticación; está pensado para uso local.

## 9. Pruebas y evidencia

Desde la raíz del repositorio con `.venv` local:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
node tests/test_presentation.cjs
node --check flood/static/app.js
node --check flood/static/help.js
```

En el equipo original sustituir `.\.venv` por `..\.venv`. Si hay restricciones de temporales, usar una carpeta exclusiva de pruebas con `--basetemp`; pytest puede limpiar esa carpeta.

Última ejecución del 5/11: **11 casos Python aprobados**, además de pruebas JavaScript de presentación. Cubren dominio seco, solución plana conocida, límites de remoción, depresión, repetibilidad, casos inválidos, API y persistencia, malla y refinamiento temporal. También se comprobaron estructura HTML, referencias DOM, rutas y estilos calculados de opacidad/bordes/selección. Esas comprobaciones no sustituyen pruebas visuales en navegador.

Evidencia de `VALIDATION.json` para humedad 0,5 y drenaje 5 mm/h:

| Escenario | Máximo del reporte | Índice medio |
|---|---:|---:|
| 50 mm en 2 h | 615,287 mm | 7,849 |
| 100 mm en 2 h | 962,874 mm | 18,067 |

Son máximos simulados concentrados, no mediciones reales. El máximo de todo el dominio puede superar al máximo del reporte. Los tiempos históricos son del equipo donde se ejecutó la prueba y no constituyen garantías de rendimiento.

Refinamiento temporal registrado: diferencias relativas L1 de aproximadamente 2,40 % (30 a 15 s) y 1,21 % (15 a 7,5 s). Sensibilidad registrada: cambiar conductancia de 20 a 10 altera el campo del reporte aproximadamente 28,9 %; reducir el margen de 1 km a 500 m lo altera 18,3 %. No son porcentajes de error frente a inundaciones reales.

`scripts/check_pilot.py` genera ejecuciones y actualiza `VALIDATION.json` y `requirements.txt`. `scripts/review_sensitivity.py` escribe `SENSITIVITY.json`. No ejecutarlos como si fueran lecturas sin efectos. Sus fechas están fijadas en el código actual; antes de generar una nueva evidencia hay que gestionar su fecha y versión explícitamente.

## 10. Limitaciones y próximos hitos

- Resolución de trabajo de 250 m: no resuelve cunetas ni desniveles de calles individuales.
- Zona parcial fija; no representa toda Santa Cruz.
- Infiltración y conductancia provisionales; drenaje hipotético uniforme.
- Borde cerrado y margen insuficientemente validado; posibles acumulaciones artificiales.
- Sin calibración local ni contraste con eventos observados.
- Sin predicción meteorológica, alertas, probabilidades ni garantía de seguridad.
- El índice se satura a 100; no expresa riesgo completo ni daños.

Sprint 2: mejorar territorio y reglas, selección de área, intervención local, SQLite y primer experimento ML. La generación de etiquetas definitivas depende de revisar el motor. Integración final: comparación A/B compatible, flujo completo y documentación final. ML aprenderá las salidas del simulador y también puede heredar sus errores.

## 11. Problemas frecuentes

| Problema | Acción |
|---|---|
| No abre localhost | Mantener el servidor iniciado; comprobar el mensaje de arranque y el puerto 5050 |
| Iniciador no encuentra Python | Revisar ubicación de `.venv`; usar el comando adecuado de la sección 2 |
| Continúa el diseño anterior | Reiniciar servidor y Ctrl+F5 |
| No aparecen calles | Comprobar conexión; usar vista local si no cargan Leaflet u OpenStreetMap |
| No se distinguen colores | Aumentar opacidad, elegir capa correcta y seleccionar una celda |
| Índice bajo con mucha lluvia | El agua puede transferirse a otras celdas; consultar máximo y explicación de la sección 4 |
| Historial vacío al clonar | Es esperado; ejecutar un escenario para crear resultados locales |
| Resultado incompatible | Usar la versión territorial correspondiente o ejecutar un escenario nuevo |
| Error al cargar territorio | Comprobar los cuatro archivos en `data/pilot-v1`; no reemplazar vacíos por ceros |
| Error al leer historial tras edición manual | Respaldar y revisar el JSON alterado; no borrar indiscriminadamente resultados |

## 12. Guion y cierre de entrega

1. Explicar que es un piloto experimental con terreno público y lluvia hipotética.
2. Mostrar terreno y señalar el área de reporte.
3. Ejecutar el ejemplo de 50 mm; seleccionar una celda y explicar el índice.
4. Mostrar opacidad, cuadrícula, ayuda y vista local.
5. Ejecutar 100 mm y observar la diferencia sin llamarla comparación A/B formal.
6. Recuperar la primera ejecución desde el historial.
7. Mostrar limitaciones y próximos pasos.

Antes de declarar cerrado el sprint, verificar manualmente:

- [ ] Arranque desde cero con instrucciones entregadas.
- [ ] Cálculo y consulta de los dos ejemplos.
- [ ] Ficha, cierre, opacidad, líneas, capas, zoom y ayuda.
- [ ] Advertencia de cambios sin ejecutar y recuperación del historial.
- [ ] Recuperación después de reiniciar el servidor.
- [ ] Cálculo y mapa local sin internet.
- [ ] Lectura del diseño en el tamaño de pantalla de la presentación.
- [ ] Instalación en otro equipo, si forma parte de la entrega exigida.

La lista representa verificaciones pendientes, no resultados ya aprobados. No se recibió una rúbrica oficial que permita afirmar conformidad total con la evaluación del docente.
