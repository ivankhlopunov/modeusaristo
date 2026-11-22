import argparse
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
OUTPUT_DIRECTORY = ROOT / "data" / "scientific_articles"
BASE_URL = "https://api.openalex.org/works"
SEARCHES = {
    "Python Developer": ["python software development", "python web application development", "python software testing"],
    "Java Developer": ["java software engineering", "spring boot development", "java application testing"],
    "Data Analyst": ["data analytics sql", "data visualization business intelligence", "data analysis methods"],
}
ALIASES = {
    "python": "Python Developer",
    "java": "Java Developer",
    "data": "Data Analyst",
    "python developer": "Python Developer",
    "java developer": "Java Developer",
    "data analyst": "Data Analyst",
    "аналитик данных": "Data Analyst",
    "all": "all",
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    temporary.replace(path)


def flatten_abstract(inverted):
    if not isinstance(inverted, dict):
        return None
    positions = []
    for word, offsets in inverted.items():
        if not isinstance(offsets, list):
            continue
        for offset in offsets:
            if isinstance(offset, int) and 0 <= offset <= 15000:
                positions.append((offset, word))
    if not positions:
        return None
    positions.sort()
    return " ".join(word for _, word in positions)[:12000]


def normalize(work, profession, search_query):
    if not isinstance(work, dict):
        return None
    work_id = str(work.get("id") or "").strip()
    title = str(work.get("display_name") or work.get("title") or "").strip()
    if not work_id or not title:
        return None
    location = work.get("primary_location") or {}
    source = location.get("source") or {}
    access = work.get("open_access") or {}
    primary_topic = work.get("primary_topic") or {}
    authors = []
    for item in (work.get("authorships") or [])[:15]:
        author = (item or {}).get("author") or {}
        if author.get("display_name"):
            authors.append(author["display_name"])
    return {
        "id": work_id.rsplit("/", 1)[-1],
        "openalex_id": work_id,
        "profession": profession,
        "search_query": search_query,
        "title": title,
        "authors": authors,
        "publication_year": work.get("publication_year"),
        "publication_date": work.get("publication_date"),
        "type": work.get("type"),
        "doi": work.get("doi"),
        "url": work.get("doi") or work_id,
        "abstract": flatten_abstract(work.get("abstract_inverted_index")),
        "cited_by_count": work.get("cited_by_count"),
        "venue": source.get("display_name"),
        "venue_type": source.get("type"),
        "venue_openalex_id": source.get("id"),
        "issn_l": source.get("issn_l"),
        "issn": source.get("issn") or [],
        "is_open_access": access.get("is_oa"),
        "open_access_url": access.get("oa_url"),
        "primary_topic": primary_topic.get("display_name"),
        "primary_field": (primary_topic.get("field") or {}).get("display_name"),
        "quartile": None,
        "quartile_year": None,
        "quartile_category": None,
        "quartile_source": None,
        "sjr": None,
        "core_rank": None,
        "core_rank_year": None,
        "core_rank_source": None,
        "rank_status": "not_enriched",
        "source": "openalex",
        "collected_at": now_iso(),
    }


class RequestStopped(Exception):
    pass


class APIClient:
    def __init__(self, max_requests, delay, api_key):
        self.max_requests = max_requests
        self.delay = delay
        self.api_key = api_key
        self.calls = 0
        self.last_call = 0.0

    def get(self, query, per_page, year_from, year_to, page):
        parameters = {
            "search": query,
            "filter": f"from_publication_date:{year_from}-01-01,to_publication_date:{year_to}-12-31,type:article",
            "per_page": per_page,
            "page": page,
        }
        if self.api_key:
            parameters["api_key"] = self.api_key
        url = BASE_URL + "?" + urlencode(parameters)
        for attempt in range(3):
            if self.calls >= self.max_requests:
                raise RequestStopped("Достигнут лимит HTTP-запросов")
            elapsed = time.monotonic() - self.last_call
            if elapsed < self.delay:
                time.sleep(self.delay - elapsed)
            self.calls += 1
            self.last_call = time.monotonic()
            headers = {"User-Agent": "ModeusAristo-Research-Scout/1.0", "Accept": "application/json"}
            request = Request(url, headers=headers)
            try:
                with urlopen(request, timeout=30) as response:
                    data = json.load(response)
                if not isinstance(data, dict) or not isinstance(data.get("results"), list):
                    raise RequestStopped("Неожиданный формат ответа OpenAlex")
                return data
            except HTTPError as error:
                if error.code in (401, 403):
                    raise RequestStopped(f"OpenAlex отказал в доступе: HTTP {error.code}") from error
                if error.code == 429:
                    raise RequestStopped("OpenAlex ограничил запросы: HTTP 429. Сбор остановлен") from error
                if error.code not in (500, 502, 503, 504):
                    raise RequestStopped(f"Ошибка OpenAlex: HTTP {error.code}") from error
                print(f"HTTP {error.code}, попытка {attempt + 1}/3")
            except (URLError, TimeoutError, OSError) as error:
                print(f"Сетевая ошибка {type(error).__name__}, попытка {attempt + 1}/3")
            if attempt < 2:
                time.sleep((2 ** attempt) + random.uniform(0, 0.5))
        raise RequestStopped("OpenAlex недоступен после трёх попыток")


def read_previous(path, resume):
    if not resume or not path.is_file():
        return {}, set()
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    articles = {}
    for article in data.get("articles", []):
        if isinstance(article, dict) and article.get("openalex_id"):
            articles[article["openalex_id"]] = article
    return articles, set(data.get("completed_queries", []))


def main():
    parser = argparse.ArgumentParser(description="ModeusAristo: научные статьи через OpenAlex")
    parser.add_argument("--profession", default="all")
    parser.add_argument("--target", type=int, default=120)
    parser.add_argument("--per-page", type=int, default=50)
    parser.add_argument("--max-requests", type=int, default=24)
    parser.add_argument("--max-pages-per-query", type=int, default=2)
    parser.add_argument("--delay", type=float, default=1.5)
    parser.add_argument("--year-from", type=int, default=2021)
    parser.add_argument("--year-to", type=int, default=datetime.now(timezone.utc).year)
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--api-key", default=os.getenv("OPENALEX_API_KEY", ""))
    args = parser.parse_args()
    requested = " ".join(args.profession.split())
    canonical = ALIASES.get(requested.casefold(), requested)
    if canonical != "all" and canonical not in SEARCHES:
        parser.error(f"Неизвестная профессия: {requested}")
    if not 1 <= args.target <= 5000:
        parser.error("--target должен быть от 1 до 5000")
    if not 1 <= args.max_requests <= 200:
        parser.error("--max-requests должен быть от 1 до 200")
    if not 1 <= args.per_page <= 100:
        parser.error("--per-page должен быть от 1 до 100")
    if not 1 <= args.max_pages_per_query <= 20:
        parser.error("--max-pages-per-query должен быть от 1 до 20")
    if not 0.5 <= args.delay <= 120:
        parser.error("--delay должен быть от 0.5 до 120")
    if not 1900 <= args.year_from <= args.year_to <= datetime.now(timezone.utc).year:
        parser.error("Некорректный диапазон годов")
    professions = list(SEARCHES) if canonical == "all" else [canonical]
    suffix = "all" if canonical == "all" else re.sub(r"[^a-z0-9]+", "_", canonical.casefold()).strip("_")
    output = OUTPUT_DIRECTORY / f"openalex_articles_{suffix}.json"
    existing, completed = read_previous(output, not args.no_resume)
    all_articles = existing
    client = APIClient(args.max_requests, args.delay, args.api_key)
    errors = []
    complete = False

    def save():
        atomic_json(output, {
            "schema_version": "research_articles_v1",
            "source": "openalex",
            "generated_at": now_iso(),
            "professions": professions,
            "year_from": args.year_from,
            "year_to": args.year_to,
            "articles": list(all_articles.values()),
            "total": len(all_articles),
            "completed_queries": sorted(completed),
            "collection_complete": complete,
            "errors": errors,
            "api_requests_this_run": client.calls,
            "metrics_note": "Q1-Q4, SJR и CORE не представлены OpenAlex как подтверждённые рейтинги; значения null до отдельного обогащения.",
        })

    print(f"OpenAlex: профессии {', '.join(professions)}, цель {args.target}, лимит {args.max_requests} запросов")
    print(f"Файл: {output}")
    if not args.api_key:
        print("Ключ OpenAlex не задан: допустимость и объём запросов зависят от текущих правил API")
    try:
        for profession in professions:
            for query in SEARCHES[profession]:
                for page in range(1, args.max_pages_per_query + 1):
                    job_key = f"{profession}|{query}|{args.year_from}|{args.year_to}|{page}"
                    if job_key in completed:
                        continue
                    if len(all_articles) >= args.target:
                        complete = True
                        break
                    data = client.get(query, args.per_page, args.year_from, args.year_to, page)
                    batch = data.get("results", [])
                    added = 0
                    for work in batch:
                        article = normalize(work, profession, query)
                        if article and article["openalex_id"] not in all_articles:
                            all_articles[article["openalex_id"]] = article
                            added += 1
                    completed.add(job_key)
                    save()
                    print(f"{profession} | {query} | стр. {page} | получено {len(batch)} | новых {added} | всего {len(all_articles)}")
                    if len(batch) < args.per_page:
                        break
                if complete:
                    break
            if complete:
                break
        complete = True
    except (RequestStopped, KeyboardInterrupt) as error:
        print(f"Сбор прерван: {error}")
        errors.append(str(error))
    finally:
        save()
        print(f"Сохранено {len(all_articles)} статей. Запросов за запуск: {client.calls}. Файл: {output}")


if __name__ == "__main__":
    main()
