# Fuentes y atribución

## FABDEM V1-2

Elevación: Neal, Hawker, Uhe, Paulo, Sosa, Savage y Sampson, Universidad de Bristol.

- Fuente: https://data.bris.ac.uk/datasets/s5hqmjcdj8yo2ibzi9b4ew3sn/
- DOI: https://doi.org/10.5523/bris.s5hqmjcdj8yo2ibzi9b4ew3sn
- Condiciones indicadas para la fuente: CC BY-NC-SA 4.0, https://creativecommons.org/licenses/by-nc-sa/4.0/
- Original utilizado: `S18W064_FABDEM_V1-2.tif`.
- Adaptación del proyecto: recorte piloto, reproyección a EPSG:32720 y promedio a 250 m; geometrías y pendiente derivadas.

Los productos derivados de elevación distribuidos en `data/pilot-v1` conservan la atribución y condiciones CC BY-NC-SA 4.0. Son una adaptación, sin respaldo institucional implícito. El archivo original no se incluye en Git. Las tasas de infiltración incluidas son supuestos propios provisionales; no mediciones de Bristol.

## Cobertura del suelo del piloto

ESA WorldCover 2021 v200. © ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium. La capa y los porcentajes derivados se distribuyen bajo [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). [Acceso al producto](https://esa-worldcover.org/en/data-access).

La ficha de celda muestra la composición estimada de su superficie en 2021. Cada celda de 250 m se divide en 2.500 cuadrados de 5 m y al centro de cada uno se le asigna la clase del píxel más cercano en el mapa nominal de 10 m. Esta subdivisión aproxima áreas en UTM. El código 0 cuenta como superficie sin datos. La infiltración del simulador continúa siendo provisional.

Para reproducir la preparación, colocar los dos originales `S18W064_FABDEM_V1-2.tif` y `ESA_WorldCover_10m_2021_v200_S18W066_Map.tif` en `data/raw/` y ejecutar `python scripts/prepare_territory.py` desde la raíz del proyecto con el entorno activado. El manifiesto registra los SHA-256 de los originales. La aplicación utiliza las celdas ya preparadas.

## Textura superficial de SoilGrids

La preparación usa las predicciones medias de arena y arcilla de SoilGrids 2.0 (ISRIC, 0–5 cm, 250 m, CC BY 4.0). Lee el píxel nativo en el centro de cada celda del piloto y convierte g/kg a porcentaje. Registra por separado las texturas disponibles, las ausentes y las que suman más de 100 % entre arena y arcilla. [Acceso de ISRIC](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_02.html).

Desde la raíz con el entorno Python activado, ejecutar `python scripts/prepare_soilgrids.py`. También se pueden usar dos recortes locales asignando `--source-dir CARPETA`; los archivos deben llamarse `sand_0-5cm_mean.tif` y `clay_0-5cm_mean.tif`, contener sus unidades originales (g/kg) y conservar CRS y NoData. Los nombres deben corresponder a la propiedad y profundidad descargadas.

El informe `work/soilgrids/pilot.json` guarda una fila por celda, las fuentes, la versión territorial, el resumen de cobertura y la huella de las filas. Para una textura válida calcula conductividad saturada estimada del suelo mineral en mm/h mediante `25.4 × 10^(-0.60 + 0.0126 × arena_pct − 0.0064 × arcilla_pct)`. La fracción urbanizada y la saturación del escenario requieren tratamiento separado antes de aplicar una tasa efectiva al simulador. La generación del informe es independiente del motor. [Ecuación y unidades](https://gmd.copernicus.org/articles/7/711/2014/).

El piloto distribuye la consulta revisada en `data/pilot-v1/soilgrids.json`. La API la presenta únicamente si coincide con la versión territorial. Hay textura válida en 14 de las 320 celdas del margen y en ninguna de las 256 del reporte central. En las otras 562 faltan ambas propiedades. La ficha permite consultar la textura disponible y muestra por separado la tasa base de 5 mm/h usada por el simulador.

## Calles

Mapa base: © OpenStreetMap contributors, https://www.openstreetmap.org/copyright . Las teselas se consultan en línea; no se incluyen en el repositorio. No participan en el cálculo. Leaflet 1.9.4 se carga desde CDN cuando no hay copia local; su implementación no es código propio.

## Código y otros datos

No se ha elegido una licencia de distribución para el código propio. No atribuirle automáticamente la licencia de FABDEM ni añadir MIT sin una decisión del autor. Las bibliotecas externas mantienen sus licencias respectivas. Un repositorio público no equivale a conceder una licencia de código abierto.
