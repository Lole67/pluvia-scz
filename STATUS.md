# Estado — 2026-11-03

## Terminado y comprobado
- Descarga oficial FABDEM 22,030,716 bytes: CRC y SHA256 correctos, apertura geográfica correcta.
- Malla 250 m: 576 celdas, 256 de reporte; sin vacíos, EPSG:32720.
- Simulación conservativa D4 con máximos, balance y validación de entradas.
- API Flask, guardado inmutable por ejecución y recuperación tras recrear aplicación.
- Formulario y vista SVG local implementados, recursos servidos correctamente.
- 11 pruebas automatizadas aprobadas. El primer intento tuvo un error de permisos del directorio temporal; repetición en carpeta de trabajo: 11/11.

## Decisiones de este avance
- Reutilizar código inicial y datos; no cambiar stack ni plan general.
- Zona piloto fija y parámetros sintéticos declarados para Sprint 1.
- Leaflet 1.9.4 integrado como opción «Mapa con calles», con carga desde CDN si no existen recursos locales. Vista SVG conservada para uso sin internet. La verificación visual del modo Leaflet y su instalación local siguen pendientes: no se da RF-18 por completo.
- Archivos JSON para persistencia mínima; SQLite sigue previsto para Sprint 2.
- No ML ni despliegue público en este avance.

## Pulido del Sprint 1
- Ayudas de lluvia/duración, humedad por opciones, ejemplos A/B y resumen explicativo del resultado.
- Leyenda, superficie por categoría y selección de celda más visibles. Detalles técnicos desplegables.
- Aviso de configuración modificada sin recalcular; formulario bloqueado durante ejecución.
- Resultados territoriales incompatibles se rechazan antes de cambiar el mapa.
- Mapa Leaflet opcional con referencia OpenStreetMap, zoom y centrado; carga con tiempo límite y retorno a vista local. Sin descarga masiva de mapas.
- Guion de presentación en GUIA_DEMOSTRACION.md; iniciador INICIAR.cmd.
- Comprobación de sintaxis JavaScript y pruebas de presentación (umbrales, cambios de escenario, matrices/versiones) aprobadas; 11 pruebas Python siguen aprobadas.
- Sensibilidad documentada en SENSITIVITY.json: cambiar conductancia 20→10 m²/s altera el campo de máximos del reporte un 28,9 % en norma L1 relativa; reducir margen 1000→500 m lo altera un 18,3 %. Conservación de masa correcta, pero sensibilidad material. No hay calibración física ni independencia de borde demostrada. Esto impide presentar los máximos como profundidades reales y generar etiquetas definitivas para ML sin revisar el motor.

## Pendiente antes de cerrar Sprint 1
- Revisar visualmente el recorrido en navegador y comprobar teclado, selección de celdas, cambio de capa e historial.
- Incorporar Leaflet local cuando su descarga sea accesible, manteniendo la demo sin red.
- Revisar plausibilidad territorial con el estudiante; preparar capturas y ensayo.
- Verificar instrucciones en equipo de entrega. Los criterios son internos; rúbrica del docente no aportada.

## Bloqueos
- Descargas desde el ejecutor fallan por resolución de red; el navegador y PowerShell del usuario sí tienen acceso.
- No está disponible la herramienta de control del navegador para QA visual.
- La comprobación HTTP real desde el ejecutor fue bloqueada por WinError 10013 (permisos de socket). Las pruebas Flask usan su cliente interno; no sustituyen la prueba de arranque desde PowerShell del usuario.

## Siguiente hito
Sprint 2 hasta 20/11: completar territorio, selección e intervención, persistencia SQLite, catálogo sintético, particiones y ML evaluado. Integración final hasta 4/12; defensa 7/12.

## Corrección tras captura del usuario
- La captura confirma que Leaflet y las calles cargan, pero la vista SVG permanece visible debajo y no se aprecia la superposición.
- Corregido ocultamiento del SVG mediante atributo hidden explícito; SVG no refleja la propiedad JavaScript hidden como un elemento HTML.
- Activado renderizador Canvas de Leaflet para la malla y refresco de tamaño/estilos tras mostrar el mapa. Verificación visual de esta corrección pendiente.

- Segunda captura: vista local ya oculta, calles visibles, malla ausente. GeoJSON comprobado: 576 polígonos en coordenadas de Santa Cruz. Se inicializa la vista antes de las capas y se asigna un renderer Canvas explícito en panel flood-results (z-index 450, sobre calles). Redibujado al mostrar. Verificación visual pendiente; no se afirma corrección confirmada.


## Interfaz compacta con ayuda contextual — 2026-11-03
Controles compactos, mapa ampliado, ayuda lateral modal con temas y accesos por campo. Detalles de interpretación y superficies desplegables. Se conservan IDs, simulador, historial y renderizador Leaflet. Sintaxis JS, referencias DOM y rutas Flask verificadas; 11 pruebas Python y presentación JS pasan. Inspección visual e interacción real pendientes de prueba en navegador del usuario.


## Diseño del mapa — 2026-11-05
Panel de escenario agrupado, historial desplegable, leyenda sobre el mapa y resumen de tres indicadores; tiempo de cálculo en detalles técnicos. Ficha de celda estructurada y cerrable, controles de opacidad y líneas en SVG y Leaflet, líneas adaptadas al zoom, paleta de terreno diferenciada. Se preservan datos y motor. 11 pruebas Python y pruebas JS de presentación pasan; controles de estilo, referencias DOM, estructura HTML y rutas comprobados. Sin navegador automatizado disponible: acabado visual y recorrido manual pendientes. El usuario confirmó anteriormente la superposición Leaflet.


## Documentación de entrega — 2026-11-05
Manual integral docs/SPRINT_1.md, README actualizado, guía GitHub y atribución DATA_SOURCES.md. Se distingue prototipo funcional de aceptación manual y validación física. Preparación Git local sin remoto ni publicación; identidad de autor y destino por confirmar. Se excluyen entorno, resultados personales y tesela original.


## Preparación de publicación — 2026-11-06
Nombre del repositorio: Pluvia SCZ, https://github.com/Lole67/pluvia-scz . Se integra el README inicial remoto conservando ambos historiales. Commit local inicial 2c25951. La publicación y sincronización se comprueban después del push; esta entrada no certifica por sí sola que haya finalizado.
