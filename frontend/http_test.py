from api import send_request

result = send_request(
    "Python-разработчик",
    "Разработка серверных приложений"
)

if result:
    print("Ответ сервера:")
    print(result["json"])
else:
    print("Не удалось получить ответ")