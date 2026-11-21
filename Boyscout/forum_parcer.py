
import calendar
import json
import re
import time

from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse
from html import unescape
import feedparser 
import requests
from bs4 import BeautifulSoup


BASE_URL = "https://qna.habr.com"
LATEST_RSS = BASE_URL + "/rss/questions_latest/"

DATA_DIR = Path(__file__).resolve().parent / "data"

MAX_AGE_DAYS = 365

PROFESSIONS = {
    "Python Developer": [
        "python",
        "django",
        "fastapi"
    ],
    "Java Developer": [
        "java",
        "spring",
    ],
    "Data Analyst": [
        "sql",
        "pandas",
    ]
}

HEADERS = {
    "User-Agent": "ModeusAristoBoyScout/1.0",
    "Accept": "application/rss+xml, application/xml, text/xml"
}


def clean_html(text):
    soup = BeautifulSoup(str(text or ""), "html.parser")
    return soup.get_text(" ", strip=True)


def normalize(text):
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def get_rss(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=15
    )
    response.raise_for_status()

    feed = feedparser.parse(response.content)

    if feed.bozo and not feed.entries:
        raise ValueError("Некорректный RSS: " + url)

    return feed.entries


def discover_tag_rss(tag):
 
    url = BASE_URL + "/tag/" + tag + "/questions"

    response = requests.get(url, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for link in soup.find_all("link", href=True):
        href = link["href"]
        mime = link.get("type", "")

        if "rss" in mime.lower() or "rss" in href.lower():
            rss_url = urljoin(BASE_URL, href)

            if urlparse(rss_url).hostname == "qna.habr.com":
                return rss_url

    return None


def get_date(entry):
    parsed = entry.get("published_parsed")

    if not parsed:
        parsed = entry.get("updated_parsed")

    if not parsed:
        return None

    return datetime.fromtimestamp(
        calendar.timegm(parsed),
        tz=timezone.utc
    )


def entry_to_discussion(entry, profession, tag):
    url = entry.get("link", "")

    if not url:
        return None

    if urlparse(url).hostname != "qna.habr.com":
        return None

    match = re.search(r"/q/(\d+)", url)
    if not match:
        return None

    published = get_date(entry)

    if published is None:
        return None

    cutoff = datetime.now(timezone.utc) - timedelta(
        days=MAX_AGE_DAYS
    )

    if published < cutoff:
        return None

    title = clean_html(entry.get("title"))
    text = clean_html(
        entry.get("summary") or entry.get("description")
    )

    if not title:
        return None

    return {
        "id": match.group(1),
        "profession": profession,
        "title": unescape(title),
        "text": text[:2500],
        "questions": [unescape(title)],
        "answers": [],
        "tags": [tag],
        "score": None,
        "answer_count": None,
        "url": url,
        "source": "habr_qna",
        "published_at": published.isoformat(),
        "collected_at": datetime.now(
            timezone.utc
        ).isoformat()
    }


def collect_profession(profession, tags):
    unique = {}

    for tag in tags:
        print(f"Проверяем тег: {tag}")

        try:
            rss_url = discover_tag_rss(tag)

            if not rss_url:
                print("RSS тега не найден")
                continue

            entries = get_rss(rss_url)

            for entry in entries:
                discussion = entry_to_discussion(
                    entry, profession, tag
                )

                if discussion is None:
                    continue

                unique[discussion["id"]] = discussion

        except (requests.RequestException, ValueError) as error:
            print("Ошибка источника:", error)

        time.sleep(1)

    return list(unique.values())


def main():
    all_discussions = []
    errors = []

    print("MODEUSARISTO — BOYSCOUT HABR Q&A")

    for profession, tags in PROFESSIONS.items():
        print("\nПрофессия:", profession)

        discussions = collect_profession(
            profession, tags
        )

        print("Найдено:", len(discussions))

        all_discussions.extend(discussions)

        if not discussions:
            errors.append(
                f"Нет свежих вопросов для {profession}"
            )

    result = {
        "source": "habr_qna",
        "collected_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "total": len(all_discussions),
        "forum_discussions": all_discussions,
        "errors": errors
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    filename = DATA_DIR / (
        "forums_habr_"
        + datetime.now().strftime("%Y-%m-%d")
        + ".json"
    )

    with filename.open("w", encoding="utf-8") as file:
        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2
        )

    print("\nСохранено:", filename)
    print("Всего:", len(all_discussions))
    print("Предупреждения:", errors)


if __name__ == "__main__":
    main()
