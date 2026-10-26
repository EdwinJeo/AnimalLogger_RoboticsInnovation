#importing the stuff I need to run code
import streamlit as st
import os 
import pandas as pd 
from datetime import datetime 
from google import genai 
from PIL import Image 
import urllib.parse
import requests


#Getting the page set up so that the tab thingy shows stuff 
st.set_page_config(page_title="Talos Animal Recogniser", page_icon="🐱")
st.title("Talos Animal Recogniser 🐱")

#making the history thing so that it records it 
if "history" not in st.session_state:
    st.session_state.history = []
if "score" not in st.session_state:
    st.session_state.score = 0
if "last_processed" not in st.session_state:
    st.session_state.last_processed = None


#Setting up level and progress for XP
currentLevel = (st.session_state.score // 300) + 1 # setting level
xpProgress = st.session_state.score % 300 #setting xp

#to add the xp at the top
st.metric(label="Total XP",value=f"{st.session_state.score} XP")
st.progress(min(xpProgress / 300.0, 1.0), text=f"Progress to Level {currentLevel + 1} ({xpProgress}/300 XP)") #uses progress bar to add level system 
st.divider()

#ensuring I set up the key 
if "GEMINI_API_KEY" not in os.environ:
    st.error("Please input your API Key ")
    st.stop()

#just to say use Gemini to set it up as a variable
client = genai.Client()

#the actual picture thing
picture = st.camera_input("Take a photo of an animal for me to analyse")

#to give the picture to ai i need to check i havent already done it
if picture and picture != st.session_state.last_processed:
    #sets the picture taken to a variable to ensure it doesn't get processed again 
    st.session_state.last_processed = picture

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
                contents=[Image.open(picture),prompt]
            )

            ai_description = response.text #uses the variable to make it easier

            if "No Animal Identified" in ai_description: #this way if it detects nothing it wont store or give xp 
                st.warning("No animal was detected in this photo, please take another photo") #to give user warning 
            else: #any other time just respond with this
                earned_xp = 100 #default fallback for the thing as the other stuff wont always work 
                for line in ai_description.split('\n'): #sorts through the response line by line
                    if "XP:" in line: #find the word xp within line so that it knows where to search 
                        import re 
                        nums = re.findall(r'\d+',line ) #setting a variable to the xp value - but it is string 
                        if nums: #to get the xp into the xp score thing
                            earned_xp = int(nums[0]) #adds the parsed xp score to the earned xp thingy


                animal_name = "Wildlife" #making a default fallback in case of fail
                for line in ai_description.split('\n'):#sorts through ai response line by line 
                    if "Name:" in line: #identifies part with the name of animal in it 
                        animal_name = line.replace("Name:" , "").strip() # replaces variable with the name 

                image_url = None# image url is set to none to act as a fallback 
                try:
                    formatted_query = urllib.parse.quote(animal_name) #sets a variable to give to the url as the animal name 
                    wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{formatted_query}" #gets the image using the animal name that we just got 
                    headers = {'User-Agent': 'TalosAnimalRecogniser/1.0 (Educational Project)'} #to follow the strict wikimedia guidelines

                    wiki_response = requests.get(wiki_url, headers = headers) #asking wikimedia for the picture 
                    if wiki_response.status_code == 200: #if it says yes then set the data into a file 
                        wiki_data = wiki_response.json() #settign data into a file
                        if "thumbnail" in wiki_data: #checking to see if there is a pic 
                            image_url = wiki_data["thumbnail"]["source"] #setting the image url for the pic 
                except Exception: #if not work then dont do 
                    pass

                #fallback if this doesn't work 
                display_image = image_url if image_url else Image.open(picture)


                st.session_state.score += earned_xp

                
                

                formatted_description = ai_description.replace('\n', '  \n')
                st.success(f"{formatted_description} \n\n +{earned_xp} XP added to your score!") #displays the response in a green text box
                st.balloons()
                

                analysed_items = {
                    "image" : display_image,
                    "description" : f"{formatted_description}  \n\n  {earned_xp} XP"
                }

                st.session_state.history.insert(0, analysed_items) #puts into the list at the bottom
                st.toast("Image Analysis Done") #just to say it worked

                st.rerun() #to update thing so that it shows xp 
            
        except Exception as e: #when error logic
            st.error(f"There has been an error when communicating with the AI : {e}") #displays the error and error code in a red box

#displaying the list 
st.subheader("Session History (Resets on Refresh)")
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


