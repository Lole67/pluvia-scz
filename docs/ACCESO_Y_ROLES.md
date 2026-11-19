# Acceso y roles


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


Consulta la instalación y la recuperación local de cuenta en [el manual técnico](PLUVIA_SCZ_SPRINT_1.md).
