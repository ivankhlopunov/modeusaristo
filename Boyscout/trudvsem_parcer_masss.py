import json
import os
import requests
from pathlib import Path
import re
import time
from datetime import datetime, timezone
professions = {'Python Developer': ['Python Developer', 'Python разработчик', 'Программист Python'], 'Java Developer': ['Java Developer', 'Java разработчик', 'Программист Java'], 'Data Analyst': ['Аналитик данных', 'Data Analyst', 'SQL аналитик']}
API_URL = 'https://opendata.trudvsem.ru/api/v1/vacancies'
MAX_PAGES = 1000
PAGE_SIZE = 100
MAX_TOTAL_VACANCIES = 100000
REQUEST_DELAY = 1
DATA_DIR = Path(__file__).resolve().parent / 'data'
HEADERS = {'User-Agent': 'ModeusAristoBoyScout/1.0', 'Accept': 'application/json'}

def clean(value):
    if value is None:
        return ''
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    text = str(value)
    text = re.sub('<[^>]+>', ' ', text)
    text = re.sub('\\s+', ' ', text)
    return text.strip()
SKILLS = {'Python': ['python'], 'Java': ['java'], 'Django': ['django'], 'FastAPI': ['fastapi'], 'Flask': ['flask'], 'Spring': ['spring'], 'SQL': ['sql'], 'PostgreSQL': ['postgresql', 'postgres'], 'MySQL': ['mysql'], 'Redis': ['redis'], 'RabbitMQ': ['rabbitmq'], 'Docker': ['docker'], 'Kubernetes': ['kubernetes', 'k8s'], 'Git': ['git'], 'GitLab CI': ['gitlab-ci', 'gitlab ci'], 'Linux': ['linux'], 'Pandas': ['pandas'], 'NumPy': ['numpy'], 'Power BI': ['power bi'], 'Excel': ['excel'], 'aiohttp': ['aiohttp'], 'dramatiq': ['dramatiq'], 'APScheduler': ['apscheduler']}

def extract_skills(text):
    found_skills = []
    text = text.lower()
    for skill, keywords in SKILLS.items():
        for keyword in keywords:
            pattern = '(?<![a-zа-яё0-9])' + re.escape(keyword) + '(?![a-zа-яё0-9])'
            if re.search(pattern, text):
                found_skills.append(skill)
                break
    return found_skills

def fetch_vacancies(query, offset=0, limit=100):
    params = {'text': query, 'offset': offset, 'limit': limit}
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            print(f'\nЗапрос: {query}, offset={offset}, попытка {attempt}/{max_attempts}')
            response = requests.get(API_URL, params=params, headers=HEADERS, timeout=(10, 40))
            print(f'HTTP-статус: {response.status_code}')
            if response.status_code in [500, 502, 503, 504, 429]:
                if attempt < max_attempts:
                    wait_time = 2 ** attempt
                    print(f'Сервер временно недоступен. Повтор через {wait_time} сек.')
                    time.sleep(wait_time)
                    continue
                print('Превышено количество попыток')
                return None
            response.raise_for_status()
            data = response.json()
            if str(data.get('status', '200')) != '200':
                print('Ошибка внутри JSON:', data.get('meta'))
                return None
            results = data.get('results', {})
            if not isinstance(results, dict):
                print('Неожиданный формат results')
                return None
            vacancies = results.get('vacancies', [])
            if not isinstance(vacancies, list):
                print('Неожиданный формат vacancies')
                return None
            print(f'Загружено вакансий: {len(vacancies)}')
            return vacancies
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as error:
            print(f'Ошибка подключения: {error}')
            if attempt < max_attempts:
                time.sleep(2 ** attempt)
                continue
            return None
        except requests.exceptions.RequestException as error:
            print(f'Ошибка HTTP: {error}')
            return None
        except ValueError as error:
            print(f'Ошибка обработки JSON: {error}')
            return None
    return None

def normalize_vacancy(item, profession):
    vacancy = item.get('vacancy', {})
    if not isinstance(vacancy, dict):
        return None
    vacancy_id = vacancy.get('id')
    company = vacancy.get('company') or {}
    if not isinstance(company, dict):
        company = {}
    region = vacancy.get('region') or {}
    if not isinstance(region, dict):
        region = {}
    title = clean(vacancy.get('job-name'))
    if not title:
        return None
    external_id = str(vacancy_id) if vacancy_id is not None else clean(vacancy.get('vac_url'))
    requirements = vacancy.get('requirement') or {}
    if isinstance(requirements, str):
        try:
            requirements = json.loads(requirements)
        except json.JSONDecodeError:
            requirements = {'text': requirements}
    if not isinstance(requirements, dict):
        requirements = {'text': clean(requirements)}
    responsibilities = clean(vacancy.get('duty'))
    description = clean(vacancy.get('description'))
    skills_text = ' '.join([title, responsibilities, description, clean(requirements)])
    skills = extract_skills(skills_text)
    experience = requirements.get('experience')
    result = {'id': external_id, 'profession': profession, 'name': title, 'company': clean(company.get('name')), 'region': clean(region.get('name')), 'experience': experience, 'schedule': clean(vacancy.get('schedule')), 'employment': clean(vacancy.get('employment')), 'requirements': requirements, 'responsibilities': responsibilities, 'description': description, 'skills': skills, 'url': vacancy.get('vac_url'), 'published_at': vacancy.get('creation-date'), 'source': 'trudvsem', 'is_mock': False, 'collected_at': datetime.now(timezone.utc).isoformat()}
    return result

def is_relevant_vacancy(vacancy, profession):
    title = vacancy.get('name', '').lower()
    if profession == 'Python Developer':
        return 'python' in title or 'питон' in title
    elif profession == 'Java Developer':
        return bool(re.search('\\bjava\\b', title)) and 'javascript' not in title
    elif profession == 'Data Analyst':
        return 'аналитик данных' in title or 'data analyst' in title or 'sql аналитик' in title or ('sql-аналитик' in title)
    return False

def collect_profession(profession, queries):
    print(f'\nПоиск профессии: {profession}')
    collected = {}
    for query in queries:
        print(f'\nПоисковый запрос: {query}')
        for page in range(MAX_PAGES):
            offset = page * PAGE_SIZE
            vacancies = fetch_vacancies(query=query, offset=offset, limit=PAGE_SIZE)
            if vacancies is None:
                print('Не удалось загрузить страницу')
                break
            if not vacancies:
                print('Больше вакансий нет')
                break
            print(f'Получено вакансий: {len(vacancies)}')
            for item in vacancies:
                normalized = normalize_vacancy(item, profession)
                if normalized is None:
                    continue
                if not is_relevant_vacancy(normalized, profession):
                    continue
                vacancy_id = normalized['id']
                if not vacancy_id:
                    continue
                unique_key = f'trudvsem:{vacancy_id}'
                collected[unique_key] = normalized
            time.sleep(REQUEST_DELAY)
            if len(vacancies) < PAGE_SIZE:
                break
    result = list(collected.values())
    print(f'\nНайдено уникальных вакансий для {profession}: {len(result)}')
    return result

def save_to_json(data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime('%Y-%m-%d')
    filename = DATA_DIR / f'trudvsem_{today}.json'
    tmp = filename.with_name(filename.name + '.tmp')
    try:
        with tmp.open('w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        tmp.replace(filename)
    finally:
        if tmp.exists():
            tmp.unlink()
    print(f'\nДанные сохранены: {filename}')

def save_collection_json(vacancies, completed):
    result = {'source': 'trudvsem', 'collected_at': datetime.now(timezone.utc).isoformat(), 'professions': list(professions.keys()), 'total': len(vacancies), 'vacancies': vacancies, 'collection_complete': completed, 'collection_status': 'completed' if completed else 'partial'}
    save_to_json(result)

def search_vacancies(profession, limit=10, max_pages=3):
    if limit <= 0 or max_pages <= 0:
        return []
    profession_mapping = {'python developer': 'Python Developer', 'python разработчик': 'Python Developer', 'python-разработчик': 'Python Developer', 'программист python': 'Python Developer', 'java developer': 'Java Developer', 'java разработчик': 'Java Developer', 'java-разработчик': 'Java Developer', 'программист java': 'Java Developer', 'data analyst': 'Data Analyst', 'аналитик данных': 'Data Analyst', 'sql аналитик': 'Data Analyst'}
    normalized_name = profession.strip().lower()
    canonical_profession = profession_mapping.get(normalized_name)
    if canonical_profession is None:
        raise ValueError(f'Профессия «{profession}» пока не поддерживается')
    queries = professions[canonical_profession]
    unique_vacancies = {}
    for query in queries:
        for page in range(max_pages):
            offset = page * PAGE_SIZE
            items = fetch_vacancies(query=query, offset=offset, limit=PAGE_SIZE)
            if items is None:
                break
            if not items:
                break
            for item in items:
                vacancy = normalize_vacancy(item, canonical_profession)
                if vacancy is None:
                    continue
                if not is_relevant_vacancy(vacancy, canonical_profession):
                    continue
                vacancy_id = vacancy.get('id')
                if not vacancy_id:
                    continue
                unique_key = f'trudvsem:{vacancy_id}'
                unique_vacancies[unique_key] = vacancy
                if len(unique_vacancies) >= limit:
                    return list(unique_vacancies.values())
            if len(items) < PAGE_SIZE:
                break
            time.sleep(REQUEST_DELAY)
    return list(unique_vacancies.values())
CHECKPOINT_DIR = DATA_DIR / 'checkpoints'
CHECKPOINT_ITEMS = CHECKPOINT_DIR / 'vacancies_progress.jsonl'
CHECKPOINT_STATE = CHECKPOINT_DIR / 'collection_state.json'
FAILED_PAGES = CHECKPOINT_DIR / 'failed_pages.jsonl'

def _atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    try:
        with temporary.open('w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()

def _load_progress():
    expected_queries = [[profession, query] for profession, queries in professions.items() for query in queries]
    state = {'version': 1, 'queries': expected_queries, 'query_index': 0, 'page': 0, 'limit': MAX_TOTAL_VACANCIES, 'page_size': PAGE_SIZE, 'max_pages': MAX_PAGES}
    collected = {}
    if CHECKPOINT_STATE.exists():
        with CHECKPOINT_STATE.open('r', encoding='utf-8') as file:
            loaded = json.load(file)
        for field in ('version', 'queries', 'limit', 'page_size', 'max_pages'):
            if loaded.get(field) != state[field]:
                raise ValueError('Параметры сбора изменились. Сохраните старую папку Boyscout/data/checkpoints отдельно, удалите её и запустите сбор заново.')
        state = loaded
        if not CHECKPOINT_ITEMS.exists():
            raise RuntimeError('Найден указатель прогресса без файла вакансий')
    if CHECKPOINT_ITEMS.exists() and (not CHECKPOINT_STATE.exists()):
        raise RuntimeError('Найден файл прогресса без указателя; не удаляйте его')
    if CHECKPOINT_ITEMS.exists():
        with CHECKPOINT_ITEMS.open('r', encoding='utf-8') as file:
            for line in file:
                try:
                    vacancy = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = f"{vacancy.get('source')}:{vacancy.get('id')}"
                if vacancy.get('id'):
                    collected[key] = vacancy
        print(f"Продолжаем сбор: {len(collected)} уникальных вакансий, поисковый запрос №{state['query_index'] + 1}, страница №{state['page'] + 1}")
    return (collected, state)

def _append_page(new_vacancies):
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    with CHECKPOINT_ITEMS.open('a', encoding='utf-8') as file:
        for vacancy in new_vacancies:
            file.write(json.dumps(vacancy, ensure_ascii=False) + '\n')
        file.flush()
        os.fsync(file.fileno())

def collect_massive():
    collected, state = _load_progress()
    queries = state['queries']
    for query_index in range(state['query_index'], len(queries)):
        profession, query = queries[query_index]
        first_page = state['page'] if query_index == state['query_index'] else 0
        print(f'\nПрофессия: {profession}; поиск: {query}')
        consecutive_no_new = 0
        for page in range(first_page, MAX_PAGES):
            if len(collected) >= MAX_TOTAL_VACANCIES:
                return (list(collected.values()), True)
            offset = page * PAGE_SIZE
            items = fetch_vacancies(query, offset=offset, limit=PAGE_SIZE)
            if items is None:
                CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
                with FAILED_PAGES.open('a', encoding='utf-8') as file:
                    file.write(json.dumps({
                        'profession': profession,
                        'query': query,
                        'page': page + 1,
                        'offset': offset,
                        'reason': 'API request failed',
                        'recorded_at': datetime.now(timezone.utc).isoformat()
                    }, ensure_ascii=False) + '\n')
                print(f'Ошибка на странице {page + 1} запроса {query}. Переходим к следующему запросу.')
                state['query_index'] = query_index + 1
                state['page'] = 0
                _atomic_json(CHECKPOINT_STATE, state)
                save_collection_json(list(collected.values()), False)
                break
            new_vacancies = []
            for item in items:
                vacancy = normalize_vacancy(item, profession)
                if vacancy is None or not is_relevant_vacancy(vacancy, profession):
                    continue
                vacancy_id = vacancy.get('id')
                if not vacancy_id:
                    continue
                key = f'trudvsem:{vacancy_id}'
                if key in collected:
                    continue
                collected[key] = vacancy
                new_vacancies.append(vacancy)
                if len(collected) >= MAX_TOTAL_VACANCIES:
                    break
            _append_page(new_vacancies)
            state['query_index'] = query_index
            state['page'] = page + 1
            _atomic_json(CHECKPOINT_STATE, state)
            save_collection_json(list(collected.values()), False)
            print(f'Страница {page + 1}: найдено {len(items)}, новых {len(new_vacancies)}, всего уникальных {len(collected)}')
            if new_vacancies:
                consecutive_no_new = 0
            else:
                consecutive_no_new += 1
            if consecutive_no_new >= 3:
                print('Три страницы подряд без новых подходящих вакансий. Переходим к следующему запросу.')
                break
            if len(collected) >= MAX_TOTAL_VACANCIES:
                return (list(collected.values()), True)
            if len(items) < PAGE_SIZE:
                print('Выдача по запросу закончилась')
                break
            time.sleep(REQUEST_DELAY)
        state['query_index'] = query_index + 1
        state['page'] = 0
        _atomic_json(CHECKPOINT_STATE, state)
    return (list(collected.values()), True)

def main():
    print('=' * 50)
    print('MODEUSARISTO — SCOUT')
    print('Массовый сбор вакансий «Работы России»')
    print('=' * 50)
    print(f'Максимум вакансий: {MAX_TOTAL_VACANCIES:,}')
    print(f'Максимум страниц на запрос: {MAX_PAGES}')
    all_vacancies, completed = collect_massive()
    print(f'\nВсего уникальных вакансий: {len(all_vacancies)}')
    save_collection_json(all_vacancies, completed)
    if completed:
        CHECKPOINT_STATE.unlink(missing_ok=True)
        CHECKPOINT_ITEMS.unlink(missing_ok=True)
        print('Сбор завершён. Прогресс очищен.')
    else:
        print('Сбор прерван. JSON сохранён; повторный запуск продолжит сбор.')
if __name__ == '__main__':
    main()
