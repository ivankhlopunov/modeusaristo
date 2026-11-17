
import streamlit as st
from api import send_request

st.set_page_config(
    page_title="Исследование профессий",
    page_icon="🔎",
    layout="wide"
)

st.title("Исследование профессиональной деятельности")

st.write(
    "Мультиагентная система исследования профессий"
)

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
