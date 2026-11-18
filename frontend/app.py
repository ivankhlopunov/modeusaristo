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

st.title("Исследование профессиональной деятельности")

st.write(
    "Мультиагентная система исследования профессий"
)

st.write(
    f"Завершено раундов: {st.session_state.rounds_used} / 4"
)

st.subheader("История интервью")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

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
