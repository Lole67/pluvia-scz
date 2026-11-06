# Pluvia SCZ — Cierre técnico del Sprint 1

Fecha: 6 de noviembre de 2026.

## Dictamen

El alcance funcional del piloto está implementado y los ajustes técnicos de cierre están comprobados. Se entrega como prototipo experimental: no hay validación frente a inundaciones reales ni certificación de una rúbrica docente no recibida.

La aceptación visual final y la instalación de dependencias en otro equipo no se consideran realizadas. Se conservan como verificaciones de entrega, sin mezclarlas con funciones pendientes del Sprint 2.

## Correcciones incluidas

- `INICIAR.cmd` y `start.ps1` buscan primero el entorno `.venv` interno y luego el de la carpeta padre. Ambos funcionan con rutas con espacios. El entorno interno tiene prioridad.
- Un archivo dañado o incompleto ya no bloquea todo el historial. Se validan los campos utilizados por la interfaz y las matrices antes de ofrecer un resultado.
- La interfaz informa los nombres de archivos omitidos. Ningún archivo se elimina, reescribe ni repara automáticamente.
- Consultar directamente una ejecución dañada devuelve HTTP 422 con un mensaje comprensible. Las inexistentes mantienen HTTP 404.
- `GET /api/runs` conserva su formato de lista. La interfaz solicita `?include_warnings=1` para obtener `runs` y `warnings`.

## Evidencia del 6/11

| Comprobación | Resultado y límite |
|---|---|
| Suite Python | 16 casos aprobados; cálculo, entradas, persistencia y tolerancia de historial |
| Presentación JavaScript | Umbrales, comparación de configuración y compatibilidad aprobados |
| Sintaxis de `app.js` | Aprobada por Node |
| Iniciadores | 4 combinaciones aprobadas: CMD y PowerShell, con entorno padre e interno; ejecución real de Python sobre un `run.py` de prueba en carpeta con espacios |
| Conservación del historial | Archivos dañados preservados; resultados válidos recuperables; recuperación después de restaurar archivo y recrear aplicación |
| Revisión de cambios | Solo correcciones de arranque, historial, pruebas y documentación; motor y datos territoriales sin cambios |

La comprobación de iniciadores verifica selección del intérprete y ejecución del archivo, no interacción visual con Flask. Las pruebas API usan el cliente interno de Flask. En la auditoría previa del mismo día se ejecutó una copia limpia de archivos versionados con dependencias existentes; no equivale a una instalación nueva desde internet.

## Alcance entregado

Configuración de lluvia y condiciones, cálculo conservativo simplificado sobre FABDEM, tres capas, selección de celdas, calles opcionales, vista local, controles de grilla, ayuda, historial y documentación de uso. El repositorio original fue publicado en `Lole67/pluvia-scz` con commit `2e991ab`; el commit posterior de cierre queda identificado por el historial Git.

## Verificaciones de aceptación pendientes

- Recorrer el diseño final en el navegador de presentación: capas, ficha y cierre, opacidad, líneas, ayuda y zoom.
- Comprobar historial y resultados visibles después de reiniciar el servidor.
- Mostrar el cálculo y la vista local con internet desconectado.
- Comprobar instalación en otro equipo si el docente la requiere.

El usuario confirmó previamente la cuadrícula sobre las calles; no se extrapola esa confirmación a todos los controles añadidos después.

## Fuera de este cierre

Revisión del lenguaje técnico, calibración física, suelo/cobertura, límites del dominio, selección libre, intervención local, comparación A/B y ML se atienden en etapas posteriores según prioridad. La API .NET permanece aplazada y no se implementó. La conservación de masa y los tests no eliminan la sensibilidad documentada a conductancia y bordes.
