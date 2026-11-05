# Preparación para GitHub

Publicar la carpeta `flood-app` como raíz del repositorio: debe contener `run.py`, `README.md`, `flood`, `docs`, `tests` y `data/pilot-v1`.

## Qué se incluye

- Código, pruebas, documentación y dependencias fijadas.
- Datos del piloto ya preparados para que un clon pueda ejecutarse.
- Manifiesto, atribución y evidencia numérica.

## Qué se excluye

`.gitignore` excluye entornos virtuales, cachés, secretos `.env`, claves, temporales, tesela original y ejecuciones personales de `data/runs`. No se borra ninguno de esos archivos locales.

Los datos preparados incluyen derivados FABDEM bajo las condiciones explicadas en `DATA_SOURCES.md`. No se ha decidido licencia del código propio. La visibilidad público/privado y el propietario del repositorio deben elegirse antes de publicar.

## Publicación desde PowerShell

Crear en GitHub un repositorio vacío, sin README ni licencia generados. Dentro de `flood-app`, revisar primero:

```powershell
git status --short
git diff --cached --stat
```

Si todavía no se inicializó Git:

```powershell
git init -b main
```

Agregar y revisar los archivos:

```powershell
git add .
git diff --cached --stat
```

Con nombre y correo de autor configurados por el usuario, crear el commit:

```powershell
git commit -m "Entrega Sprint 1: simulador, mapa y documentación"
```

Conectar la URL REAL del repositorio elegido y publicar (sustituir el ejemplo):

```powershell
git remote add origin https://github.com/USUARIO/REPOSITORIO.git
git push -u origin main
```

Si `origin` ya existe, comprobarlo antes de modificarlo. No usar `--force`. La autenticación se realiza con los mecanismos de GitHub/Git del usuario; no introducir tokens en el código ni en esta documentación. Si Git solicita identidad, configurar un nombre y correo propios; no usar datos inventados.

## Comprobación después de publicar

Verificar que no aparezcan `.venv`, `data/raw` ni `data/runs` y que sí aparezcan los cuatro archivos de `data/pilot-v1`. Clonar en otra carpeta y seguir la instalación del README. Registrar la URL y el commit entregado al docente. La existencia de este documento no significa que el repositorio ya esté publicado.
