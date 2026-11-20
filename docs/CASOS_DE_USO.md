# Pluvia SCZ · Casos de uso


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
