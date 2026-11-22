import streamlit as st

# Настройки страницы
st.set_page_config(
    page_title="Исследование профессий",
    page_icon="🔎",
    layout="wide"
)

# Создаём таблицы базы данных
create_tables()


# Создаём или загружаем интервью
if "interview_id" not in st.session_state:
    interview_id = get_latest_interview()

    if interview_id is None:
        interview_id = str(uuid.uuid4())
        create_interview(interview_id)

    st.session_state.interview_id = interview_id


# Загружаем историю сообщений
if "messages" not in st.session_state:
    st.session_state.messages = load_messages(
        st.session_state.interview_id
    )


# Инициализация состояния приложения
if "sources" not in st.session_state:
    st.session_state.sources = []

if "round_id" not in st.session_state:
    st.session_state.round_id = None

if "rounds_used" not in st.session_state:
    st.session_state.rounds_used = 0

if "editing_message" not in st.session_state:
    st.session_state.editing_message = None


# Заголовок приложения
st.title("Исследование профессиональной деятельности")

st.write(
    "Мультиагентная система исследования профессий"
)

# Поле для ввода профессии
profession = st.text_input(
    "Введите название профессии",
    placeholder="Например: Разработчик ПО"
)

# Дополнительное описание
description = st.text_area(
    "Дополнительное описание (необязательно)"
)

# Кнопка запуска исследования
if st.button("Начать исследование"):

    if st.button("Начать исследование"):

        if not profession.strip():
            st.warning("Введите название профессии.")

        else:
            st.success(
                f"Начинаем исследование профессии «{profession}»."
            )

        with st.spinner("Scout собирает информацию..."):

            try:

                # Отправляем запрос Scout
                response = requests.post(
                    SCOUT_URL,
                    json={
                        "profession": profession.strip(),
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