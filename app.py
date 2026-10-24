#importing the stuff I need to run code
import streamlit as st
import os 
import pandas as pd 
from datetime import datetime 
from google import genai 
from PIL import Image 

#Getting the page set up so that the tab thingy shows stuff 
st.set_page_config(page_title="Talos Animal Recogniser", page_icon="🐱")
st.title("Talos Animal Recogniser 🐱")

#making the history thing so that it records it 
if "history" not in st.session_state:
    st.session_state.history = []

#ensuring I set up the key 
if "GEMINI_API_KEY" not in os.environ:
    st.error("Please input your API Key ")
    st.stop()

#just to say use Gemini 
client = genai.Client()

#the actual picture thign
picture = st.camera_input("Take a photo of an animal for me to analyse")

#to give the picture to ai I need to initialise it 
if picture:
    img = Image.open(picture)

    #cool spinning animation to show smth happening
    with st.spinner("We are currently processing the image "):

        #give the image to the ai 
        try:
            response = client.models.generate_content(
                model= 'gemini-3.5-flash-lite' , 
                contents=[img,"Describe what animal you see in this image in one word, as well as this on a new line please add the population of the species, then on another line add the species endangerment do this in a simple readable format that is readable and coherent. But if it is not an animal just reply with this is not an animal "]
            )

            ai_description = response.text #uses the variable to make it easier
            st.success(f"{ai_description} ") #displays the response in a green text box

            st.session_state.history.insert(0, ai_description) #puts into the list at the bottom
            st.toast("Image Analysis Done") #just to say it worked
            
        except Exception as e: #when error logic
            st.error(f"There has been an error when communicating with the AI : {e}") #displays the error and error code in a red box

#displaying the list 
st.subheader("session history (resets on refresh)")
if st.session_state.history:
    for item in st.session_state.history:
        st.write(f"•{item}") #appending to the history list
else:
    st.info("Nothing has been sent to analyse") # what to show when nothing is there


