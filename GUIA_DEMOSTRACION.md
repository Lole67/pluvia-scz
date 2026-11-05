# Demostración del Sprint 1 — 3 a 5 minutos

## Preparación

1. Si hay una versión anterior ejecutándose, detenerla con Ctrl+C.
2. Abrir `INICIAR.cmd` o usar el comando de README.md.
3. Abrir http://127.0.0.1:5050 y actualizar con Ctrl+F5 para cargar la interfaz nueva.
4. Probar «Mapa con calles» antes de presentar. Si no carga, usar «Vista sin internet»: los datos y el cálculo siguen siendo los mismos. Las calles no están almacenadas en el paquete.

## Recorrido y explicación

**Inicio:** «Este prototipo permite explorar acumulación pluvial bajo supuestos. Usa un modelo público del terreno de una zona de Santa Cruz. Todavía no incorpora aprendizaje automático ni representa inundaciones observadas».

**Terreno:** mostrar «Altura del terreno». «Cada celda tiene 250 por 250 metros. Calculamos en 36 km² y resumimos la zona central de 16 km². Las celdas del margen también aportan agua. El margen y el borde siguen siendo provisionales».

**Ejemplo A:** pulsar «Ejemplo A · 50 mm» y luego «Ejecutar». «Suponemos 50 mm en dos horas: 25 mm por hora. La humedad inicial es intermedia y el drenaje hipotético retira hasta 5 mm por hora. No son mediciones de la Alcaldía».

**Resultado:** leer el resumen, seleccionar una celda y cambiar a «Agua máxima simulada». «El resultado muestra el máximo de cada celda durante el evento. Puede superar la lluvia de esa celda porque recibe agua de sus vecinas. Esa cantidad no está validada como profundidad real».

**Ejemplo B:** cargar 100 mm. Antes de ejecutar, señalar el aviso de configuración modificada: el mapa aún muestra A. Ejecutar B y observar cambios. Ambos ejemplos mantienen duración, humedad y drenaje; solo cambia la lluvia. No afirmar que es una comparación A/B formal ni que todas las celdas cambian igual.

**Historial:** recuperar A. «El resultado estaba guardado: no se calculó nuevamente y conserva sus entradas».

**Detalle técnico, si lo preguntan:** abrir «Parámetros y comprobación del agua». «Se contabilizan lluvia, infiltración, drenaje y almacenamiento. El residuo numérico es pequeño. Esto comprueba conservación, no precisión respecto a inundaciones reales».

## Preguntas que debes poder responder

- **¿De dónde sale el terreno?** FABDEM V1-2, Universidad de Bristol; agregado desde aproximadamente 30 m a una malla de 250 m.
- **¿Qué significa 80?** 80 puntos del índice provisional, equivalente a 80 mm simulados. No significa 80 % de probabilidad. El índice se limita a 100 aunque la acumulación sea mayor.
- **¿Por qué cambia con el drenaje?** Es una tasa hipotética de remoción limitada por el agua disponible; no representa tuberías reales.
- **¿Dónde está la IA?** Se incorporará en Sprint 2 para aproximar resultados del simulador; aprenderá de simulaciones, no de un historial real.
- **¿Qué falta mejorar?** Cobertura e infiltración, dominio y bordes, calibración de parámetros, validación territorial y funciones de siguientes hitos.
- **¿Se puede usar para alertas?** No. Es una demostración exploratoria académica.

## Comprobación manual pendiente de registrar

- [ ] Abrir y reconocer la zona; probar mapa con calles y vista local.
- [ ] Ejecutar A y B; verificar resumen, leyenda y selección de celdas.
- [ ] Cambiar valores sin ejecutar: debe aparecer el aviso y mantenerse el resultado anterior.
- [ ] Rechazar lluvia negativa o duración cero mediante el formulario.
- [ ] Recuperar una ejecución y verificar sus parámetros.
- [ ] Reiniciar y comprobar que el historial persiste.
- [ ] Usar vista local sin conexión y volver a calcular.
- [ ] Revisar presentación a tamaño de pantalla de la defensa y con teclado.

Las casillas están pendientes; no son evidencia de pruebas realizadas. El usuario consideró adecuada la versión visual anterior, pero esta revisión aún necesita comprobarse en navegador.
