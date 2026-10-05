# Reels lyrics automáticos → Facebook (GitHub Actions)

Todos los días a las **14:00 y 18:00 (Uruguay)** genera un reel de máx. 25 s (o hasta donde termine el audio) y lo publica en tu **Página** de Facebook.

## 1. Subir el repo
1. Creá un repo en GitHub y subí todo este contenido.
2. Las fotos de fondo se toman de la misma carpeta de Drive que los audios (abajo). `assets/backgrounds/` queda solo como respaldo.

## 2. Google Drive (gratis)
1. Poné los audios en una carpeta de Drive → *Compartir → Cualquier persona con el enlace (lector)*.
2. Copiá el ID de la carpeta (lo que va después de `/folders/` en la URL).
3. En https://console.cloud.google.com creá un proyecto → habilitá **Google Drive API** → *Credenciales → Crear clave de API*.

Fotos: usá **otra carpeta de Drive** (también compartida como "Cualquier persona con el enlace") con todas las fotos que quieras (jpg/png/webp). Cada reel sortea 4 distintas.

Opcionales en Drive:
- `tema__s45.mp3` → el clip arranca en el segundo 45 (ideal para el estribillo).
- `tema.srt` con el mismo nombre → usa esa letra en vez de la transcripción automática.

## 3. Facebook
Solo funciona con **Páginas** (no perfiles personales).
1. https://developers.facebook.com → crear app (tipo Empresa) y agregarte como admin/desarrollador.
2. En Graph API Explorer: permisos `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `publish_video`. Generá el token de usuario.
3. Convertilo a larga duración y pedí `GET /me/accounts`: ahí sale el **ID de la Página** y su **token de Página** (el derivado de un token de larga duración no vence).

## 4. Secrets (Settings → Secrets and variables → Actions)
`GOOGLE_API_KEY`, `DRIVE_FOLDER_ID` (audios), `DRIVE_PHOTOS_FOLDER_ID` (fotos), `FB_PAGE_ID`, `FB_PAGE_TOKEN`

## 5. Probar
Actions → *Reels diarios* → **Run workflow** con `dry_run` activado: te deja `reel_preview.mp4` para descargar. Después probá con `dry_run` apagado (publica de inmediato).

## Notas
- Una ejecución diaria (07:17 UY, con respaldo 09:17) genera los 2 reels de hoy y los deja **programados en Facebook** (14:00-14:08 y 18:00-18:08 UY). Facebook los publica a la hora, sin depender de GitHub. Funciona en repo privado.
- Primera vez: Run workflow con `test_schedule` para verificar que Facebook acepte programar Reels.
- Las canciones rotan sin repetirse hasta que suenan todas (`state/used.json`).
- Ajustes de estilo (zoom, oscuridad, púrpura, espejo, tamaños) en `src/config.py`.
- Repo privado: la ejecución diaria dura ~20-30 min (unos 600-900 min/mes de los 2000 gratis).
