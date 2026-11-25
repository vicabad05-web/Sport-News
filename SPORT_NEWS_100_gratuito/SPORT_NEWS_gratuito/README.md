# SPORT NEWS — versión 100 % gratuita

Revista digital deportiva para alumnado de ESO. No utiliza APIs de pago, bases de datos de pago, IA de pago ni servicios externos de alojamiento de pago.

## Qué incluye
- Página web estática, adaptable a móvil y ordenador.
- Noticias de feeds RSS de medios deportivos.
- Filtro estricto de las últimas 24 horas, calculado desde la hora de ejecución.
- Noticias sin fecha de publicación fiable descartadas.
- Deduplicación por URL y titular normalizado.
- Clasificación deportiva básica por palabras clave.
- Resumen breve a partir del texto descriptivo que proporciona cada RSS.
- Actualización automática diaria mediante GitHub Actions.
- Sin apartado «Reto del día» ni «Debate del día».

## Coste
**0 €/mes** usando un repositorio público de GitHub y GitHub Pages, dentro de los límites y condiciones gratuitos de GitHub. No compres dominio ni actives servicios de pago. GitHub Actions puede tener límites y restricciones de uso; este flujo está pensado para una ejecución diaria ligera.

## Publicar la web (una sola vez)
1. Entra en https://github.com y crea una cuenta o inicia sesión.
2. Crea un repositorio **público** llamado `sport-news`.
3. Sube todos los archivos de esta carpeta conservando su estructura.
4. En el repositorio, entra en **Settings → Pages**.
5. En «Build and deployment», selecciona **Deploy from a branch**.
6. Selecciona la rama `main` y la carpeta `/ (root)`. Guarda.
7. Entra en **Actions** y permite los workflows si GitHub lo solicita.
8. Ejecuta manualmente el workflow «Actualizar SPORT NEWS» desde Actions → Update SPORT NEWS → Run workflow.
9. La web aparecerá en `https://TU-USUARIO.github.io/sport-news/`.

## Actualización diaria a las 08:00 de Madrid
GitHub Actions programa las tareas en UTC y no admite zona horaria IANA en cron. Por eso hay dos disparadores:
- 06:00 UTC: corresponde a las 08:00 en Madrid durante el horario de verano.
- 07:00 UTC: corresponde a las 08:00 en Madrid durante el horario de invierno.

El script comprueba la hora local `Europe/Madrid` y solo recopila cuando son las 08:00. GitHub puede iniciar los cron con algunos minutos de retraso, por lo que no se garantiza el minuto exacto. La ventana de noticias siempre será de las 24 horas inmediatamente anteriores a la ejecución real.

## Añadir o quitar periódicos
Edita `sources.json`. Cada fuente necesita un nombre y una URL RSS. No todos los periódicos ofrecen RSS completos o estables; algunos feeds pueden cambiar o bloquear peticiones. El informe mostrará las fuentes que hayan podido consultarse.

## Importante sobre noticias e imágenes
Se muestran titulares, resúmenes breves derivados de los RSS, atribución y enlaces al medio original. No se copia el artículo completo. Las imágenes solo se muestran cuando el feed facilita una URL de imagen. Respeta las condiciones de uso de cada medio.

## Limitaciones honestas
- Los RSS pueden no incluir todas las noticias publicadas por un periódico.
- Si un feed no ofrece fecha de publicación, esa noticia se excluye para respetar el filtro estricto.
- Los resúmenes no son generados por IA: se utiliza el extracto que proporciona el propio RSS, limpiado y acotado.
- Las reglas de clasificación son automáticas y pueden necesitar ajustes.
- Las tareas programadas de GitHub pueden retrasarse ocasionalmente.
