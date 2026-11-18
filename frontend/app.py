import streamlit as st
from api import send_request

st.set_page_config(
    page_title="Исследование профессий",
    page_icon="🔎",
    layout="wide"
)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "sources" not in st.session_state:
    st.session_state.sources = []

if "interview_id" not in st.session_state:
    st.session_state.interview_id = None

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

            for message in st.session_state.messages[i + 1:]:
                message["stale"] = True

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
    st.session_state.messages.append({
        "role": "user",
        "content": user_message
    })

    st.rerun()

profession = st.text_input(
    "Введите название профессии",
    placeholder="Например: Разработчик ПО"
)

description = st.text_area(
    "Дополнительное описание (необязательно)"
)

if st.button("Начать исследование"):

    if profession.strip():

        result = send_request(
            profession.strip(),
            description.strip()
        )

        if result:
            st.success("Ответ успешно получен!")

            st.json(result["json"])

        else:
            st.error("Не удалось получить ответ от сервера.")

    else:
        st.warning("Введите название профессии.")
