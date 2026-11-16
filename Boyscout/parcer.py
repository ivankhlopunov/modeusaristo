
import requests
import json
from pathlib import Path
profession = input('Введите профессию: ').strip()
if not profession:
    print('Введите профессию, а не рустую строку')
    raise SystemExit(1)

URL = 'https://api.hh.ru/vacancies'
params = {'text':profession, 'per_page':10, 'page':0}
headers = {'HH-User-Agent': 'ModeusAristoScout/1.0 (rodionmihelidze@gmail.com)', "Accept": "application/json"}
try:
    response = requests.get(
        URL, params = params, headers = headers, timeout = 15
    )

    print("Статус ответа:", response.status_code)
    print("Ответ сервера:", response.text[:2000])
    response.raise_for_status()

    data = response.json()
except requests.HTTPError as error:
    print("Ошибка HTTP:", error)
    print("Код ответа:", error.response.status_code)
    print("Ответ hh.ru:", error.response.text[:2000])
    raise SystemExit(1)

except requests.RequestException as error:
    print("Ошибка соединения:", error)
    raise SystemExit(1)

vacancies = []
for vacancy in data.get('items', []):
    result = {
        'id': vacancy.get('id'),
        'name': vacancy.get('name'),
        'company': vacancy.get('employer', {}).get('name'),
        'salary': vacancy.get('salary'),
        'url': vacancy.get('alternate_url'),
        'source':'hh-ru'
    }
    vacancies.append(result)

data_folder = Path(__file__).resolve().parent / 'data'
data_folder.mkdir(exist_ok = True)
result_data = {'profession': profession,
               'vacancies': vacancies}
with open(file_path, 'w', encoding = 'utf-8') as file:
    json.dump(
        result_data,
        file,
        ensure_ascii = False,
        indent = 4
    )

print(f"полученно вакансий: {len(vacancies)}")
print(f"Данные сохранены в файл: {file_path}")
