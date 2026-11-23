# Sprint 2 en el piloto de Santa Cruz

El piloto calcula sobre 576 celdas de 250 m. El reporte inicial cubre 16 km² y el dominio completo, 36 km². La interfaz permite elegir todo el piloto o dibujar un reporte. La superficie de cada categoría y el índice medio consideran la fracción de celda intersectada. Dibujar un reporte cambia el resumen, mientras el cálculo sigue abarcando todo el dominio.

## Demostración local

1. Desde la raíz ejecutar `.\INICIAR.cmd`, abrir http://127.0.0.1:5050 e iniciar sesión.
2. Configurar 50 mm, 2 horas, saturación 0,5 y drenaje general de 5 mm/h. Seleccionar lluvia uniforme, marcar «Usar ML experimental si es compatible» y simular. El resultado identifica el árbol de regresión y puede recuperarse del historial.
3. Abrir «Área de reporte e intervención», elegir «Dibujar intervención», marcar tres vértices distintos en el mapa local y establecer la tasa local en 10 mm/h. Simular otra vez. La aplicación debe identificar el simulador y mostrar su balance de agua. El drenaje local sustituye al general en la fracción cubierta de cada celda.
4. Elegir «Dibujar reporte» y delimitar otro polígono. Las superficies por categoría deben sumar el área de ese reporte. Con 250 mm, incluso sin intervención, la aplicación utiliza el simulador porque el modelo fue entrenado hasta 150 mm.

## Entrenamiento y evaluación

Con el entorno Python del proyecto activado, ejecutar `python -m pip install scikit-learn==1.9.1` y `python scripts/train_surrogate.py`. La ejecución ordinaria de la web carga el modelo ya preparado. El entrenamiento genera los parámetros de cada escenario en `data/pilot-v1/ml/catalog.json`, las etiquetas en mm por celda en `catalog.npz` y el árbol, variables, límites, bloques y métricas en `model.json`.

La corrida con semilla 42 generó 70 escenarios distintos. Se usaron 47 para entrenar, 12 para validar y 11 para probar. Los 16 bloques de 6 × 6 celdas se repartieron en 10, 3 y 3 respectivamente. Cada partición usa únicamente sus escenarios y sus bloques. La etiqueta es la acumulación máxima calculada por el simulador. La línea base predice la media de entrenamiento y se comparan una regresión lineal y un árbol sobre log(1 + mm). El árbol incorpora desnivel hacia el vecino más bajo, celdas aportantes y profundidad hasta el rebose. Se activa si mejora el MAE y el acierto de categoría respecto al modelo lineal en validación.

| Partición | Modelo | MAE (mm) | RMSE (mm) | R² |
|---|---|---:|---:|---:|
| Validación | Media | 76,50 | 98,96 | −0,109 |
| Validación | Lineal | 50,54 | 79,24 | 0,289 |
| Validación | Árbol | 29,38 | 86,97 | 0,143 |
| Prueba | Media | 122,37 | 236,07 | −0,008 |
| Prueba | Lineal | 90,97 | 196,34 | 0,302 |
| Prueba | Árbol | 54,68 | 147,67 | 0,605 |

En prueba, el árbol acertó el 86,2 % de las categorías y la inferencia tomó aproximadamente 0,71 ms para la matriz de características ya preparada. El tiempo total de la aplicación incluye cargar datos, iniciar Python y generar el resultado. Los errores de aproximación siguen siendo altos. La evaluación utiliza datos sintéticos del simulador y no mide precisión frente a inundaciones observadas.

La infiltración base es provisional (5 mm/h). SoilGrids aporta textura en 14 celdas del margen y en ninguna del reporte central. La cobertura urbana que queda fuera del piloto y la comparación A/B no forman parte de esta demostración.

### Aciertos por categoría y detección desde 50 mm

Desde la carpeta del proyecto se puede reproducir la evaluación del modelo y catálogo guardados en PowerShell:

```powershell
& ..\.venv\Scripts\python.exe .\scripts\train_surrogate.py --evaluar
```

Cada observación es una celda en un escenario reservado. La tabla muestra las 1.188 observaciones de prueba. Las filas corresponden al simulador y las columnas al árbol. Los cortes son 25, 50 y 75 mm.

| Simulador / ML | Baja | Media | Alta | Muy alta |
|---|---:|---:|---:|---:|
| Baja | 886 | 7 | 6 | 21 |
| Media | 16 | 2 | 2 | 1 |
| Alta | 11 | 3 | 0 | 5 |
| Muy alta | 71 | 10 | 11 | 136 |

La categoría exacta coincide en 1.024 de 1.188 casos (86,2 %). Si la pregunta es dónde se alcanzan al menos 50 mm, alta y muy alta cuentan juntas. El modelo detecta 152 de los 247 casos señalados por el simulador (61,5 %), omite 95 y marca 30 adicionales. De sus 182 marcas, 152 coinciden con el simulador (83,5 %).

Con el mismo umbral en validación se obtienen 139 detecciones, 58 omisiones y 39 marcas adicionales. La referencia en ambas particiones es la acumulación máxima simulada.
