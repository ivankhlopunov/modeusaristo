import streamlit as st
import uuid

from api import (
    send_request,
    get_professions,
    get_vacancies,
    get_discussions,
    get_knowledge_base
)
from database import create_tables, create_interview, save_message, load_messages, get_latest_interview, update_message, mark_following_stale

create_tables()

if "interview_id" not in st.session_state:
    interview_id = get_latest_interview()

    if interview_id is None:
        interview_id = str(uuid.uuid4())
        create_interview(interview_id)

    st.session_state.interview_id = interview_id

st.set_page_config(
    page_title="Исследование профессий",
    page_icon="🔎",
    layout="wide"
)

if "messages" not in st.session_state:
    st.session_state.messages = load_messages(
        st.session_state.interview_id
    )

    if st.session_state.get("interview_id"):
        st.session_state.messages = load_messages(
            st.session_state.interview_id
        )

if "sources" not in st.session_state:
    st.session_state.sources = []

if "round_id" not in st.session_state:
    st.session_state.round_id = None

if "rounds_used" not in st.session_state:
    st.session_state.rounds_used = 0

if "editing_message" not in st.session_state:
    st.session_state.editing_message = None

st.title("Исследование профессиональной деятельности")

st.write(
    "Мультиагентная система исследования профессий"
)

st.write(
    f"Завершено раундов: {st.session_state.rounds_used} / 4"
)

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

            st.session_state.editing_message = None
            st.rerun()

    if st.button("Отмена"):
        st.session_state.editing_message = None
        st.rerun()

if st.session_state.sources:
    st.subheader("Источники информации")

    for source in st.session_state.sources:
        st.write(source)

user_message = st.chat_input("Введите ваш ответ...")

if user_message:
    message_id = save_message(
        st.session_state.interview_id,
        "user",
        user_message
    )

    st.session_state.messages.append({
        "id": message_id,
        "role": "user",
        "content": user_message,
        "stale": False
    })

    st.rerun()


st.subheader("Данные о профессии")

professions = get_professions()

if professions:
    profession = st.selectbox(
        "Выберите профессию",
        professions
    )
else:
    profession = None
    st.error("Не удалось получить список профессий из FastAPI.")

description = st.text_area(
    "Дополнительное описание (необязательно)",
    key="profession_description"
)

if profession and st.button(
    "Загрузить данные профессии",
    key="load_profession_data"
):

    vacancies = get_vacancies(profession)
    discussions = get_discussions(profession)
    knowledge_base = get_knowledge_base(profession)

    st.subheader("Вакансии")
    if vacancies is not None:
        st.write(f"Найдено вакансий: {len(vacancies)}")
        st.json(vacancies)
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

if profession and st.button(
    "Начать исследование",
    key="start_research"
):

    result = send_request(
        profession,
        description.strip()
    )

    if result:
        st.success("Ответ успешно получен!")
        st.json(result["json"])
    else:
        st.error("Не удалось получить ответ от сервера.")
