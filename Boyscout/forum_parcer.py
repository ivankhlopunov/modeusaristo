import json
import time
from datetime import datetime, timezone
from pathlib import Path
import requests
from bs4 import BeautifulSoup
BASE_URL = "https://api.stackexchange.com/2.3"
DATA_DIR = Path(__file__).resolve().parent / "data"
REQUEST_TIMEOUT = 15
MAX_QUESTIONS = 20
PROFESSIONS = {
    "Python Developer": [
        "python django",
        "python fastapi",
        "python разработка"
    ],

    "Java Developer": [
        "java spring",
        "java backend",
        "java разработка"
    ],

    "Data Analyst": [
        "sql анализ данных",
        "python pandas",
        "аналитика данных"
    ]
}

def clean_html(html):

    if not html:
        return ""

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    return soup.get_text(
        separator=" ",
        strip=True
    )

def api_request(endpoint, params):
    url = f"{BASE_URL}/{endpoint}"

    try:

        response = requests.get(
            url,
            params=params,
            timeout=REQUEST_TIMEOUT
        )

        print(
            f"HTTP {response.status_code}: "
            f"{endpoint}"
        )

        response.raise_for_status()

        data = response.json()

        backoff = data.get("backoff", 0)

        if backoff:
            print(f"API требует паузу: {backoff} сек.")
            time.sleep(backoff)

        return data

    except requests.RequestException as error:

        print(f"Ошибка запроса: {error}")

        return None

    except ValueError:

        print("Ошибка обработки JSON")

        return None

def search_questions(query, limit=10):

    params = {
        "site": "ru.stackoverflow",
        "q": query,
        "sort": "relevance",
        "order": "desc",
        "pagesize": limit,
        "filter": "withbody"
    }

    data = api_request(
        "search/advanced",
        params
    )

    if data is None:
        return []

    return data.get("items", [])

def get_answers(question_ids):
    if not question_ids:
        return {}

    ids = ";".join(
        str(question_id)
        for question_id in question_ids
    )

    params = {
        "site": "ru.stackoverflow",
        "sort": "votes",
        "order": "desc",
        "pagesize": 100,
        "filter": "withbody"
    }

    data = api_request(
        f"questions/{ids}/answers",
        params
    )

    if data is None:
        return {}

    answers_by_question = {}

    for answer in data.get("items", []):

        question_id = answer.get("question_id")

        answers_by_question.setdefault(
            question_id,
            []
        )

        if len(answers_by_question[question_id]) >= 2:
            continue

        answers_by_question[question_id].append({
            "text": clean_html(
                answer.get("body", "")
            )[:1500],

            "score": answer.get("score", 0),

            "is_accepted": answer.get(
                "is_accepted",
                False
            )
        })

    return answers_by_question

def normalize_discussion(
    question,
    profession,
    answers
):

    question_id = question.get("question_id")

    if question_id is None:
        return None

    title = clean_html(
        question.get("title", "")
    )

    text = clean_html(
        question.get("body", "")
    )

    return {
        "id": str(question_id),

        "profession": profession,

        "title": title,

        "text": text[:2000],

        "questions": [title],

        "answers": answers,

        "tags": question.get("tags", []),

        "score": question.get("score", 0),

        "answer_count": question.get(
            "answer_count",
            0
        ),

        "url": question.get("link"),

        "source": "stackoverflow_ru",

        "published_at": datetime.fromtimestamp(
            question.get("creation_date", 0),
            tz=timezone.utc
        ).isoformat(),

        "collected_at": datetime.now(
            timezone.utc
        ).isoformat()
    }


def collect_profession(profession, queries):

    print("\n" + "=" * 50)
    print(f"Профессия: {profession}")
    print("=" * 50)

    unique_questions = {}

    for query in queries:

        print(f"\nПоиск: {query}")

        questions = search_questions(
            query,
            limit=10
        )

        for question in questions:

            question_id = question.get("question_id")

            if question_id is None:
                continue

            unique_questions[question_id] = question

        time.sleep(1)

    questions = list(
        unique_questions.values()
    )[:MAX_QUESTIONS]

    print(
        f"Уникальных вопросов: {len(questions)}"
    )

    question_ids = [
        question["question_id"]
        for question in questions
    ]

    answers_by_question = get_answers(
        question_ids
    )

    discussions = []

    for question in questions:

        question_id = question["question_id"]

        answers = answers_by_question.get(
            question_id,
            []
        )

        discussion = normalize_discussion(
            question,
            profession,
            answers
        )

        if discussion:
            discussions.append(discussion)

    return discussions

def save_json(data):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    filename = (
        DATA_DIR /
        f"forums_{today}.json"
    )

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=4
        )

    print(f"\nДанные сохранены: {filename}")

def main():

    print("=" * 50)
    print("MODEUSARISTO — FORUM SCOUT")
    print("=" * 50)

    all_discussions = []

    for profession, queries in PROFESSIONS.items():

        discussions = collect_profession(
            profession,
            queries
        )

        all_discussions.extend(discussions)

    result = {
        "source": "stackoverflow_ru",

        "collected_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "total": len(all_discussions),

        "forum_discussions": all_discussions
    }

    save_json(result)

    print("\n" + "=" * 50)
    print(
        f"ВСЕГО ОБСУЖДЕНИЙ: "
        f"{len(all_discussions)}"
    )
    print("=" * 50)

if __name__ == "__main__":
    main()