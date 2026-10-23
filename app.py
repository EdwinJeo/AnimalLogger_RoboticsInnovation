import streamlit as st
import os 
import pandas as pd 
from datetime import datetime 
from google import genai 
from PIL import Image 

st.set_page_config(page_title="AI Based Animal Logger", page_icon="🐱")
st.title("AI Photo Logger 🐱")

if "history" not in st.session_state:
    st.session_state.history = []

if "GEMINI_API_KEY" not in os.environ:
    st.error("yo we need the api key to work")
    st.stop()


client = genai.Client()

picture = st.camera_input("Take a photo of an animal for me to analyse")

if picture:
    img = Image.open(picture)

    with st.spinner("yo boy i am processing the photo"):
        try:
            response = client.models.generate_content(
                model= 'gemini-3.5-flash-lite' , 
                contents=[img,"Describe what animal you see in this image in one word, as well as this on a new line please add the population of the species, then on another line add the species endangerment do this in a simple readable format that is readable and coherent"]
            )
            print("Google got it")

            ai_description = response.text
            st.success(f"{ai_description} ")

            st.session_state.history.insert(0, ai_description)
            st.toast("yo boy the analysis done")
        except Exception as e:
            st.error(f"error communicating with the ai bro: {e}")

st.subheader("session history (resets on refresh)")
if st.session_state.history:
    for item in st.session_state.history:
        st.write(f"•{item}")
else:
    st.info("you havent analysed anything")


