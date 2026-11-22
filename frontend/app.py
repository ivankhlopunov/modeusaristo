
import streamlit as st
import uuid

from api import (
    send_request,
    get_professions,
    get_vacancies,
    get_discussions,
    get_knowledge_base,
    build_persona,
    get_question,
    ask_expert,
    compose_via_n8n
)

from database import (
    create_tables,
    create_interview,
    save_message,
    load_messages,
    get_latest_interview,
    update_message,
    mark_following_stale
)


st.set_page_config(
    page_title="Исследование профессий",
    page_icon="🔎",
    layout="wide"
)

create_tables()


# Создание или загрузка интервью
if "interview_id" not in st.session_state:
    interview_id = get_latest_interview()

    if interview_id is None:
        interview_id = str(uuid.uuid4())
        create_interview(interview_id)

    st.session_state.interview_id = interview_id


if "messages" not in st.session_state:
    st.session_state.messages = load_messages(
        st.session_state.interview_id
    )


# Состояние приложения
defaults = {
    "sources": [],
    "rounds_used": 0,
    "editing_message": None,
    "scout_result": None,
    "persona": None,
    "facts": [],
    "suggested_question": "",
    "map_result": None,
    "active_profession": None,
    "active_level": None
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# Получение значения из нескольких возможных полей
def get_field(data, *names, default="Не указано"):
    for name in names:
        value = data.get(name)

        if value is not None and value != "":
            return value

    return default


# Красивое отображение описания вакансии
def display_description(description):

    field_names = {
        "education": "Образование",
        "experience": "Опыт работы",
        "requirements": "Требования",
        "responsibilities": "Обязанности",
        "skills": "Навыки",
        "employment": "Занятость",
        "schedule": "График работы"
    }

    if isinstance(description, dict):

        for key, value in description.items():

            name = field_names.get(
                key,
                key.replace("_", " ").capitalize()
            )

            if isinstance(value, (dict, list)):
                st.markdown(f"**{name}:**")
                display_description(value)
            else:
                st.markdown(f"**{name}:** {value}")

    elif isinstance(description, list):

        for item in description:
            display_description(item)

    elif description:
        st.write(description)


# Отображение вакансий карточками

def display_vacancies(vacancies):

    if isinstance(vacancies, dict):
        vacancies = (
            vacancies.get("vacancies")
            or vacancies.get("items")
            or vacancies.get("data")
            or []
        )

    if not isinstance(vacancies, list):
        st.warning("Не удалось распознать формат списка вакансий.")
        return

    if not vacancies:
        st.info("Вакансии не найдены.")
        return

    st.write(f"Найдено вакансий: {len(vacancies)}")

    field_names = {
        "education": "Образование",
        "experience": "Опыт работы",
        "requirements": "Требования",
        "responsibilities": "Обязанности",
        "skills": "Навыки",
        "employment": "Занятость",
        "schedule": "График работы"
    }

    for vacancy in vacancies:

        if not isinstance(vacancy, dict):
            continue

        title = get_field(
            vacancy, "title", "name", "vacancy_name",
            "position", "job_title",
            default="Название вакансии не указано"
        )

        company = get_field(
            vacancy, "company", "employer",
            "company_name", "organization", "employer_name"
        )

        salary = get_field(
            vacancy, "salary", "salary_text",
            "compensation", "salary_range"
        )

        location = get_field(
            vacancy, "location", "city",
            "area", "region", "address"
        )

        description = get_field(
            vacancy, "description", "snippet",
            "requirements", "responsibilities",
            default=""
        )

        url = get_field(
            vacancy, "url", "link",
            "alternate_url", "vacancy_url",
            default=""
        )

        with st.container(border=True):

            st.markdown(f"### {title}")

            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**Компания:** {company}")
                st.write(f"**Город:** {location}")

            with col2:
                st.write(f"**Зарплата:** {salary}")

            if description:
                st.markdown("**Описание вакансии:**")

                if isinstance(description, dict):
                    for key, value in description.items():
                        name = field_names.get(
                            key,
                            key.replace("_", " ").capitalize()
                        )
                        st.markdown(f"**{name}:** {value}")

                elif isinstance(description, list):
                    for item in description:
                        if isinstance(item, dict):
                            for key, value in item.items():
                                name = field_names.get(
                                    key,
                                    key.replace("_", " ").capitalize()
                                )
                                st.markdown(f"**{name}:** {value}")
                        else:
                            st.write(item)

                else:
                    st.write(description)

            if isinstance(url, str) and url.startswith(("http://", "https://")):
                st.link_button("Открыть вакансию", url)


# Вспомогательная функция для истории агентов
def get_history():
    history = []

    for message in st.session_state.messages:
        if not message.get("stale", False):
            history.append({
                "role": message["role"],
                "content": message["content"]
            })

    return history


# Сохранение сообщения
def add_message(role, content):
    message_id = save_message(
        st.session_state.interview_id,
        role,
        content
    )

    st.session_state.messages.append({
        "id": message_id,
        "role": role,
        "content": content,
        "stale": False
    })


# Заголовок
st.title("Исследование профессиональной деятельности")

st.write(
    "Мультиагентная система исследования профессий"
)

st.write(
    f"Завершено раундов: {st.session_state.rounds_used} / 4"
)


# История интервью
st.subheader("История интервью")

for i, message in enumerate(st.session_state.messages):

    with st.chat_message(message["role"]):
        st.write(message["content"])

        if message.get("stale", False):
            st.caption("Устаревшее сообщение")

        if message["role"] == "user":
            if st.button("Редактировать", key=f"edit_{i}"):
                st.session_state.editing_message = i
                st.rerun()


# Редактирование сообщения
if st.session_state.editing_message is not None:

    i = st.session_state.editing_message

    st.subheader("Редактирование сообщения")

    edited_text = st.text_area(
        "Исправьте текст",
        value=st.session_state.messages[i]["content"],
        key=f"edited_text_{i}"
    )

    if st.button("Сохранить изменения"):

        if edited_text.strip():

            st.session_state.messages[i]["content"] = edited_text.strip()

            update_message(
                st.session_state.messages[i]["id"],
                edited_text.strip()
            )

            for message in st.session_state.messages[i + 1:]:
                message["stale"] = True

            mark_following_stale(
                st.session_state.interview_id,
                st.session_state.messages[i]["id"]
            )

            st.session_state.map_result = None

            st.session_state.editing_message = None
            st.rerun()

    if st.button("Отмена"):
        st.session_state.editing_message = None
        st.rerun()


# Данные о профессии
st.subheader("Данные о профессии")

professions = get_professions()

if professions:

    profession = st.selectbox(
        "Выберите профессию",
        professions
    )

    level = st.selectbox(
        "Выберите уровень специалиста",
        ["Junior", "Middle", "Senior"]
    )

else:

    profession = None
    level = None

    st.error(
        "Не удалось получить список профессий из FastAPI."
    )


# Загрузка данных профессии
if profession and st.button(
    "Загрузить данные профессии",
    key="load_profession_data"
):

    vacancies = get_vacancies(profession)
    discussions = get_discussions(profession)
    knowledge_base = get_knowledge_base(profession)

    st.subheader("Вакансии")

    if vacancies is not None:
        display_vacancies(vacancies)
    else:
        st.error("Не удалось загрузить вакансии.")

    st.subheader("Обсуждения")

    if discussions is not None:
        st.write(f"Найдено обсуждений: {len(discussions)}")
        st.json(discussions)
    else:
        st.error("Не удалось загрузить обсуждения.")

    st.subheader("База знаний")

    if knowledge_base is not None:
        st.json(knowledge_base)
    else:
        st.error("Не удалось загрузить базу знаний.")


# Начало исследования
if profession and level and st.button(
    "Начать исследование",
    key="start_research"
):

    with st.spinner("Подготавливаем исследование..."):

        # Получаем данные Scout
        scout = send_request(profession, level)

        if scout is None:
            st.error("Не удалось получить данные Scout.")

        else:

            st.session_state.scout_result = scout

            # Создаём синтетическую персону
            persona_result = build_persona(profession)

            if persona_result is None:
                st.error("Не удалось создать профиль специалиста.")

            else:

                st.session_state.persona = persona_result["persona"]
                st.session_state.facts = persona_result["facts"]

                st.session_state.active_profession = profession
                st.session_state.active_level = level

                st.session_state.rounds_used = 0
                st.session_state.map_result = None

                # Получаем первый вариант вопроса
                question_result = get_question(
                    "Предложи первый возможный вопрос для интервью.",
                    get_history()
                )

                if question_result is None:
                    st.error("Interviewer не смог предложить вопрос.")

                else:
                    st.session_state.suggested_question = (
                        question_result["question"]
                    )

                    st.success(
                        "Исследование начато! Профиль специалиста создан."
                    )


# Интервью
if st.session_state.persona is not None:

    st.divider()
    st.subheader("Интервью с экспертом")

    st.write(
        f"Профессия: {st.session_state.active_profession}"
    )

    st.write(
        f"Уровень: {st.session_state.active_level}"
    )

    st.write(
        f"Раунд: {st.session_state.rounds_used} / 4"
    )

    if st.session_state.rounds_used < 4:

        # Предложение Interviewer
        if st.session_state.suggested_question:

            st.info(
                "Предложение Interviewer:\n\n"
                + st.session_state.suggested_question
            )

        # Поле собственного вопроса
        user_question = st.text_area(
            "Выберите или измените вопрос для Expert",
            value=st.session_state.suggested_question,
            key="expert_question"
        )

        if st.button(
            "Задать вопрос Expert",
            key="ask_expert_button"
        ):

            if not user_question.strip():

                st.warning("Введите вопрос.")

            else:

                with st.spinner("Expert готовит ответ..."):

                    history = get_history()

                    # Отправляем вопрос пользователем
                    add_message("user", user_question.strip())

                    answer_result = ask_expert(
                        user_question.strip(),
                        st.session_state.persona,
                        st.session_state.facts,
                        history
                    )

                    if answer_result is None:

                        st.error("Не удалось получить ответ Expert.")

                    else:

                        # Сохраняем ответ Expert
                        add_message(
                            "assistant",
                            answer_result["answer"]
                        )

                        st.session_state.rounds_used += 1
                        st.session_state.map_result = None

                        # Предлагаем следующий вопрос
                        if st.session_state.rounds_used < 4:

                            question_result = get_question(
                                answer_result["answer"],
                                get_history()
                            )

                            if question_result is not None:

                                st.session_state.suggested_question = (
                                    question_result["question"]
                                )

                            else:

                                st.session_state.suggested_question = ""

                                st.warning(
                                    "Не удалось получить следующий вопрос. "
                                    "Можно ввести свой."
                                )

                        else:

                            st.session_state.suggested_question = ""

                st.rerun()

    else:

        st.success("Все четыре раунда интервью завершены!")


# Источники информации
if st.session_state.sources:

    st.subheader("Источники информации")

    for source in st.session_state.sources:
        st.write(source)


# Формирование карты профессии
st.divider()
st.subheader("Карта профессии")

if st.session_state.persona is not None:

    if st.button(
        "Сформировать карту профессии",
        key="compose_profession_map"
    ):

        transcript = []

        for message in st.session_state.messages:

            if not message.get("stale", False):

                transcript.append({
                    "id": str(message["id"]),
                    "speaker": message["role"],
                    "text": message["content"]
                })

        if not transcript:

            st.warning("История интервью пока пуста.")

        else:

            with st.spinner("Synthesizer формирует карту профессии..."):

                result = compose_via_n8n(
                    st.session_state.active_profession,
                    st.session_state.active_level,
                    transcript,
                    st.session_state.scout_result
                )

            if result:

                st.session_state.map_result = result

                st.success("Карта профессии сформирована!")

            else:

                st.error(
                    "Не удалось сформировать карту профессии."
                )


# Отображение карты
if st.session_state.map_result:

    st.subheader("Результат Synthesizer")
    st.json(st.session_state.map_result)
