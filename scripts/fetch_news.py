import json
import re
import hashlib
import html
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SOURCES_FILE = ROOT / "sources.json"
OUTPUT_FILE = ROOT / "data" / "news.json"
MADRID = ZoneInfo("Europe/Madrid")
CATEGORIES = {
    "Baloncesto": ["baloncesto", "basketball", "nba", "euroliga", "acb"],
    "Tenis": ["tenis", "tennis", "atp", "wta", "wimbledon", "roland garros"],
    "Motor": ["fórmula 1", "formula 1", "formula one", "f1", "motogp", "moto gp", "rally"],
    "Atletismo": ["atletismo", "athletics", "maratón", "marathon", "running"],
    "Balonmano": ["balonmano", "handball"],
    "Ciclismo": ["ciclismo", "cycling", "tour de france", "giro d'italia", "vuelta a españa"],
    "Fútbol": ["fútbol", "football", "soccer", "champions league", "premier league", "laliga", "liga"]
}

def clean_text(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()

def child_text(item, names):
    for name in names:
        el = item.find(name)
        if el is not None and el.text:
            return el.text.strip()
    return ""

def parse_date(item):
    raw = child_text(item, ["pubDate", "{http://purl.org/dc/elements/1.1/}date", "{http://www.w3.org/2005/Atom}published", "{http://www.w3.org/2005/Atom}updated"])
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            return None
        return dt.astimezone(timezone.utc)
    except Exception:
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                return None
            return dt.astimezone(timezone.utc)
        except Exception:
            return None

def get_link(item):
    link = child_text(item, ["link"])
    if link:
        return link
    atom = item.find("{http://www.w3.org/2005/Atom}link")
    if atom is not None:
        return atom.attrib.get("href", "")
    return ""

def get_image(item):
    for el in item.iter():
        tag = el.tag.lower()
        if tag.endswith("thumbnail") or tag.endswith("content") or tag.endswith("enclosure"):
            url = el.attrib.get("url") or el.attrib.get("href")
            if url and url.startswith("http"):
                return url
    return ""

def classify(text):
    low = text.lower()
    for category, terms in CATEGORIES.items():
        if any(term in low for term in terms):
            return category
    return "Otros deportes"

def summarize(description, title):
    desc = clean_text(description)
    if not desc or desc.lower() == clean_text(title).lower():
        return "El medio ha publicado esta información. Accede a la noticia original para consultar todos los detalles."
    if len(desc) > 360:
        desc = desc[:357].rsplit(" ", 1)[0] + "…"
    return desc

def main():
    now = datetime.now(timezone.utc)
    local_now = now.astimezone(MADRID)
    # En los disparadores dobles de GitHub Actions, solo se ejecuta el de las 08:00 de Madrid.
    import os

is_manual = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"

if local_now.hour != 8 and not is_manual:
    print(f"Saltando ejecución: hora de Madrid {local_now:%H:%M}, no son las 08:00.")
    return

    cutoff = now - timedelta(hours=24)
    sources = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    articles = []
    errors = []

    for source in sources:
        try:
            request = urllib.request.Request(
                source["url"],
                headers={"User-Agent": "SPORT-NEWS-Educational-RSS/1.0 (+https://github.com)"}
            )
            with urllib.request.urlopen(request, timeout=18) as response:
                payload = response.read()
            root = ET.fromstring(payload)
            items = root.findall(".//item")
            if not items:
                items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

            for item in items:
                title = clean_text(child_text(item, ["title", "{http://www.w3.org/2005/Atom}title"]))
                link = get_link(item)
                pub = parse_date(item)
                if not title or not link or not pub:
                    continue
                # Filtro estricto: solo publicación original entre ahora-24h y ahora.
                if pub < cutoff or pub > now:
                    continue
                description = child_text(item, ["description", "summary", "{http://www.w3.org/2005/Atom}summary", "content"])
                text_for_category = f"{title} {description}"
                canonical = link.split("#", 1)[0].rstrip("/")
                title_key = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
                uid = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
                articles.append({
                    "id": uid,
                    "title": title,
                    "summary": summarize(description, title),
                    "source": source["name"],
                    "country": source.get("country", ""),
                    "url": link,
                    "image": get_image(item),
                    "published_at": pub.isoformat(),
                    "category": classify(text_for_category)
                })
        except Exception as exc:
            errors.append({"source": source.get("name", "Fuente"), "error": str(exc)[:180]})

    # Deduplicar por URL y por titular normalizado.
    unique = []
    seen_urls = set()
    seen_titles = set()
    for article in sorted(articles, key=lambda a: a["published_at"], reverse=True):
        url_key = article["url"].split("#", 1)[0].rstrip("/")
        title_key = re.sub(r"[^a-z0-9]+", " ", article["title"].lower()).strip()
        if url_key in seen_urls or title_key in seen_titles:
            continue
        seen_urls.add(url_key)
        seen_titles.add(title_key)
        unique.append(article)

    data = {
        "generated_at": now.isoformat(),
        "generated_at_madrid": local_now.isoformat(),
        "window_start": cutoff.isoformat(),
        "window_end": now.isoformat(),
        "window_hours": 24,
        "source_count": len(sources),
        "article_count": len(unique),
        "errors": errors,
        "articles": unique
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"SPORT NEWS: {len(unique)} noticias de las últimas 24 horas.")
    if errors:
        print(f"Fuentes con error: {len(errors)}")

if __name__ == "__main__":
    main()
