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
if "score" not in st.session_state:
    st.session_state.score = 0

#to add the xp at the top
st.metric(label="Total XP",value=f"{st.session_state.score} XP")
st.divider()

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

        prompt = """Analyze this image and provide the response in this exact format:
        Name: [Common name of the animal]
        Endangerment: [Conservation status e.g., Least Concern, Vulnerable, Endangered]
        Population: [Brief detail about its global or local population trend]
        Eco-Fact: [One short, kid-friendly fact on how it helps the ecosystem]
        XP: [Give it an XP score between 50 and 200 based on how rare or interesting it is, just write the number]
        Please note that if the image does not show an animal then respond with 'No Animal Identified'
        """

        #give the image to the ai 
        try:
            response = client.models.generate_content(
                model= 'gemini-3.5-flash-lite' , 
                contents=[img,prompt]
            )

            ai_description = response.text #uses the variable to make it easier

            earned_xp = 100 #default fallback for the thing as the other stuff wont always work 
            for line in ai_description.split('\n'): #sorts through the response line by line
                if "XP:" in line: #find the word xp within line so that it knows where to search 
                    import re 
                    nums = re.findall(r'\d+',line ) #setting a variable to the xp value - but it is string 
                    if nums: #to get the xp into the xp score thing
                        earned_xp = int(nums[0]) #adds the parsed xp score to the earned xp thingy

            st.session_state.score += earned_xp

            formatted_description = ai_description.replace('\n', '  \n')
            st.success(f"{formatted_description} \n\n +{earned_xp} XP added to your score!") #displays the response in a green text box
            st.balloons()

            analysed_items = {
                "image" : img,
                "description" : f"{formatted_description}  \n\n  {earned_xp} XP"
            }

            st.session_state.history.insert(0, analysed_items) #puts into the list at the bottom
            st.toast("Image Analysis Done") #just to say it worked
            
        except Exception as e: #when error logic
            st.error(f"There has been an error when communicating with the AI : {e}") #displays the error and error code in a red box

#displaying the list 
st.subheader("session history (resets on refresh)")
if st.session_state.history:
    for item in st.session_state.history:
        #setting up column
        col1, col2 = st.columns([1,2])
        
        #to display image in first column
        with col1:
            st.image(item["image"],width="content")

        #to display info in second column
        with col2:
            st.success(item["description"])

        st.divider()
else:
    st.info("Nothing has been sent to analyse") # what to show when nothing is there


