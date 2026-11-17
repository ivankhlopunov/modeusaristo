import streamlit as st
import requests

# Адрес API Scout
SCOUT_URL = "http://127.0.0.1:8000/scout/search"

# Настройки страницы
st.set_page_config(
    page_title="Исследование профессий",
    page_icon="🔎",
    layout="wide"
)

# Заголовок приложения
st.title("Исследование профессиональной деятельности")

# Описание приложения
st.write(
    "Мультиагентная система исследования профессий"
)

# Поле для ввода профессии
profession = st.text_input(
    "Введите название профессии",
    placeholder="Например: Разработчик ПО"
)

# Выбор уровня специалиста
level = st.selectbox(
    "Уровень специалиста",
    ["Junior", "Middle", "Senior"]
)

# Дополнительное описание
description = st.text_area(
    "Дополнительное описание (необязательно)"
)

# Кнопка запуска исследования
if st.button("Начать исследование"):

    if not profession.strip():
        st.warning("Введите название профессии.")

    else:

        with st.spinner("Scout собирает информацию..."):

            try:

                # Отправляем запрос Scout
                response = requests.post(
                    SCOUT_URL,
                    json={
                        "profession": profession.strip(),
                        "level": level
                    },
                    timeout=30
                )

                # Проверяем HTTP-ошибки
                response.raise_for_status()

                # Получаем JSON
                scout_data = response.json()

                st.success(
                    f"Scout завершил исследование профессии «{profession}»."
                )

                # Предупреждение о тестовых данных
                if scout_data.get("data_mode") == "mock":

                    st.info(
                        "Сейчас используются демонстрационные данные Scout."
                    )

                # Показываем вакансии
                st.subheader("Найденные вакансии")

                vacancies = scout_data.get("vacancies", [])

                for vacancy in vacancies:

                    with st.expander(
                        vacancy.get("name", "Без названия")
                    ):

                        st.write(
                            "Компания:",
                            vacancy.get("company")
                        )

                        st.write(
                            "Навыки:",
                            vacancy.get("skills", [])
                        )

                        st.write(
                            "Требования:",
                            vacancy.get("requirements", [])
                        )

                        st.write(
                            "Обязанности:",
                            vacancy.get("responsibilities", [])
                        )

                # Показываем обсуждения
                st.subheader("Профессиональные обсуждения")

                discussions = scout_data.get(
                    "forum_discussions", []
                )

                for discussion in discussions:

                    with st.expander(
                        discussion.get("title", "Обсуждение")
                    ):

                        st.write(
                            discussion.get("text", "")
                        )

                        st.write(
                            "Вопросы:",
                            discussion.get("questions", [])
                        )

                # Полный JSON для разработчиков
                with st.expander("Посмотреть полный JSON Scout"):

                    st.json(scout_data)

            except requests.RequestException as error:

                st.error(
                    "Не удалось подключиться к Scout."
                )

                st.code(str(error))