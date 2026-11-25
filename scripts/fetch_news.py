
import os
import json
import re
import html
import hashlib
import urllib.request
import xml.etree.ElementTree as ET

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo


# ==========================================
# CONFIGURACIÓN GENERAL
# ==========================================

ROOT = Path(__file__).resolve().parents[1]

SOURCES_FILE = ROOT / "sources.json"
OUTPUT_FILE = ROOT / "data" / "news.json"

MADRID = ZoneInfo("Europe/Madrid")

CATEGORIES = {
    "Fútbol": [
        "fútbol", "football", "soccer", "champions league",
        "premier league", "laliga", "liga", "real madrid",
        "barcelona", "atlético"
    ],
    "Baloncesto": [
        "baloncesto", "basketball", "nba", "euroliga", "acb"
    ],
    "Tenis": [
        "tenis", "tennis", "atp", "wta", "wimbledon",
        "roland garros"
    ],
    "Motor": [
        "fórmula 1", "formula 1", "formula one",
        "f1", "motogp", "moto gp", "rally"
    ],
    "Atletismo": [
        "atletismo", "athletics", "maratón",
        "marathon", "running"
    ],
    "Balonmano": [
        "balonmano", "handball"
    ],
    "Ciclismo": [
        "ciclismo", "cycling", "tour de france",
        "giro d'italia", "vuelta a españa"
    ]
}


# ==========================================
# LIMPIEZA DE TEXTO
# ==========================================

def clean_text(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def child_text(item, names):
    for name in names:
        element = item.find(name)

        if element is not None and element.text:
            return element.text.strip()

    return ""


# ==========================================
# FECHAS DE PUBLICACIÓN
# ==========================================

def parse_date(item):

    date_fields = [
        "pubDate",
        "{http://purl.org/dc/elements/1.1/}date",
        "{http://www.w3.org/2005/Atom}published",
        "{http://www.w3.org/2005/Atom}updated"
    ]

    raw_date = child_text(item, date_fields)

    if not raw_date:
        return None

    try:
        date = parsedate_to_datetime(raw_date)

        if date.tzinfo is None:
            return None

        return date.astimezone(timezone.utc)

    except Exception:
        pass

    try:
        date = datetime.fromisoformat(
            raw_date.replace("Z", "+00:00")
        )

        if date.tzinfo is None:
            return None

        return date.astimezone(timezone.utc)

    except Exception:
        return None


# ==========================================
# ENLACES E IMÁGENES
# ==========================================

def get_link(item):

    link = child_text(item, ["link"])

    if link:
        return link

    atom_link = item.find(
        "{http://www.w3.org/2005/Atom}link"
    )

    if atom_link is not None:
        return atom_link.attrib.get("href", "")

    return ""


def get_image(item):

    for element in item.iter():

        tag = element.tag.lower()

        if (
            tag.endswith("thumbnail")
            or tag.endswith("content")
            or tag.endswith("enclosure")
        ):

            url = (
                element.attrib.get("url")
                or element.attrib.get("href")
            )

            if url and url.startswith("http"):
                return url

    return ""


# ==========================================
# CLASIFICACIÓN DEPORTIVA
# ==========================================

def classify(text):

    text = text.lower()

    for category, keywords in CATEGORIES.items():

        for keyword in keywords:

            if keyword in text:
                return category

    return "Otros deportes"


# ==========================================
# RESÚMENES
# ==========================================

def summarize(description, title):

    description = clean_text(description)

    if (
        not description
        or description.lower() == clean_text(title).lower()
    ):

        return (
            "Consulta la noticia original para conocer "
            "todos los detalles de esta información deportiva."
        )

    if len(description) > 360:

        description = (
            description[:357].rsplit(" ", 1)[0] + "…"
        )

    return description


# ==========================================
# RECOPILACIÓN DE NOTICIAS
# ==========================================

def main():

    now = datetime.now(timezone.utc)

    local_now = now.astimezone(MADRID)

    # Permitir pruebas manuales desde GitHub Actions.
    # Las ejecuciones automáticas solo recopilan a las 08:00.

    is_manual = (
        os.environ.get("GITHUB_EVENT_NAME")
        == "workflow_dispatch"
    )

    if local_now.hour != 8 and not is_manual:

        print(
            f"Ejecución omitida: son las "
            f"{local_now:%H:%M} en Madrid."
        )

        return

    # Ventana estricta de las últimas 24 horas.

    cutoff = now - timedelta(hours=24)

    sources = json.loads(
        SOURCES_FILE.read_text(encoding="utf-8")
    )

    articles = []
    errors = []

    print("Iniciando recopilación SPORT NEWS...")

    for source in sources:

        source_name = source.get("name", "Fuente")

        try:

            request = urllib.request.Request(
                source["url"],
                headers={
                    "User-Agent": (
                        "SPORT-NEWS-Educational-RSS/1.0"
                    )
                }
            )

            with urllib.request.urlopen(
                request,
                timeout=20
            ) as response:

                payload = response.read()

            root = ET.fromstring(payload)

            items = root.findall(".//item")

            # Compatibilidad con feeds Atom.

            if not items:

                items = root.findall(
                    ".//{http://www.w3.org/2005/Atom}entry"
                )

            source_articles = 0

            for item in items:

                title = clean_text(
                    child_text(
                        item,
                        [
                            "title",
                            "{http://www.w3.org/2005/Atom}title"
                        ]
                    )
                )

                link = get_link(item)

                published = parse_date(item)

                # Descartar noticias sin fecha verificable.

                if not title or not link or not published:
                    continue

                # Filtro estricto: entre ahora y hace 24 horas.

                if published < cutoff or published > now:
                    continue

                description = child_text(
                    item,
                    [
                        "description",
                        "summary",
                        "{http://www.w3.org/2005/Atom}summary",
                        "content"
                    ]
                )

                full_text = f"{title} {description}"

                canonical_url = (
                    link.split("#", 1)[0].rstrip("/")
                )

                article_id = hashlib.sha256(
                    canonical_url.encode("utf-8")
                ).hexdigest()[:16]

                article = {
                    "id": article_id,
                    "title": title,
                    "summary": summarize(
                        description,
                        title
                    ),
                    "source": source_name,
                    "country": source.get("country", ""),
                    "url": link,
                    "image": get_image(item),
                    "published_at": published.isoformat(),
                    "category": classify(full_text)
                }

                articles.append(article)

                source_articles += 1

            print(
                f"{source_name}: "
                f"{source_articles} noticias encontradas."
            )

        except Exception as error:

            errors.append({
                "source": source_name,
                "error": str(error)[:180]
            })

            print(
                f"Error en {source_name}: {error}"
            )

    # ======================================
    # ELIMINAR NOTICIAS DUPLICADAS
    # ======================================

    unique_articles = []

    seen_urls = set()
    seen_titles = set()

    articles.sort(
        key=lambda article: article["published_at"],
        reverse=True
    )

    for article in articles:

        url_key = (
            article["url"]
            .split("#", 1)[0]
            .rstrip("/")
        )

        title_key = re.sub(
            r"[^a-z0-9]+",
            " ",
            article["title"].lower()
        ).strip()

        if (
            url_key in seen_urls
            or title_key in seen_titles
        ):
            continue

        seen_urls.add(url_key)
        seen_titles.add(title_key)

        unique_articles.append(article)

    # ======================================
    # GUARDAR RESULTADOS
    # ======================================

    data = {

        "generated_at": now.isoformat(),

        "generated_at_madrid": local_now.isoformat(),

        "window_start": cutoff.isoformat(),

        "window_end": now.isoformat(),

        "window_hours": 24,

        "source_count": len(sources),

        "article_count": len(unique_articles),

        "errors": errors,

        "articles": unique_articles
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_FILE.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("--------------------------------")

    print(
        f"SPORT NEWS: "
        f"{len(unique_articles)} noticias recopiladas."
    )

    print(
        f"Fuentes con errores: {len(errors)}"
    )

    print(
        "Ventana: últimas 24 horas."
    )

    print("--------------------------------")


# ==========================================
# INICIO DEL PROGRAMA
# ==========================================

if __name__ == "__main__":

    main()

