#importing the stuff I need to run code
import streamlit as st
import os 
import pandas as pd 
from datetime import datetime 
from google import genai 
from PIL import Image 
import urllib.parse
import requests
import pydeck as pdk
import re


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
        GlobalPoints: [Provide 6 to 10 pairs of latitude and longitude coordinates representing its worldwide habitat regions. CRITICAL: If the animal is domesticated or global like a cat or dog, distribute points across North America, South America, Europe, Asia, Africa, and Australia so it covers the whole world!]
        If there are multiple animals, separate each animal block with '---' on its own line.

        Please note that if the image does not show an animal then respond with 'No Animal Identified'
        """

        #give the image to the ai 
        try:
            response = client.models.generate_content(
                model= 'gemini-3.5-flash-lite' , 
                contents=[Image.open(picture),prompt]
            )

            ai_description = response.text #uses the variable to make it easier

            if "No Animal Identified" in ai_description: 
                st.warning("No animal was detected in this photo, please take another photo") 
            else: 
                animal_blocks = ai_description.split("---") 
                total_earned_xp = 0  
                
                for block in animal_blocks:
                    if not block.strip():
                        continue

                    earned_xp = 100 
                    for line in block.split('\n'): # <-- FIXED: parses individual block lines
                        if "XP:" in line: 
                            nums = re.findall(r'\d+', line) 
                            if nums:
                                earned_xp = int(nums[0])

                    animal_name = "Wildlife" 
                    for line in block.split('\n'): # <-- FIXED: parses individual block lines
                        if "Name:" in line: 
                            animal_name = line.replace("Name:" , "").strip() 

                    #getting the data for heatmap to work
                    heatmap_data = [] 
                    clean_description_lines = [] 
                    for line in block.split('\n'): # <-- FIXED: parses individual block lines
                        if "GlobalPoints:" in line: 
                            points_str = line.replace("GlobalPoints:", "").strip() 
                            pairs = points_str.split(';') 
                            for pair in pairs: 
                                if ',' in pair: 
                                    try:  
                                        lat_str, lon_str = pair.split(',') 
                                        heatmap_data.append({"lat": float(lat_str.strip()), "lon": float(lon_str.strip())}) 
                                    except ValueError: 
                                        pass
                        else:
                            clean_description_lines.append(line)

                    clean_description = "\n".join(clean_description_lines).strip() 
                    formatted_description = clean_description.replace('\n',  '  \n') 
                    df_heatmap = pd.DataFrame(heatmap_data) 

                    image_url = None
                    try:
                        formatted_query = urllib.parse.quote(animal_name) 
                        wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{formatted_query}" 
                        headers = {'User-Agent': 'TalosAnimalRecogniser/1.0 (Educational Project)'} 

                        wiki_response = requests.get(wiki_url, headers = headers) 
                        if wiki_response.status_code == 200: 
                            wiki_data = wiki_response.json() 
                            if "thumbnail" in wiki_data: 
                                image_url = wiki_data["thumbnail"]["source"] 
                    except Exception: 
                        pass

                    display_image = image_url if image_url else Image.open(picture)
                    total_earned_xp += earned_xp

                    analysed_items = {
                        "image" : display_image,
                        "description" : f"{formatted_description}  \n\n  {earned_xp} XP",
                        "heatmap" : df_heatmap 
                    }

                    st.session_state.history.insert(0, analysed_items) 

                st.session_state.score += total_earned_xp
                st.success(f"Successfully processed animals! Total +{total_earned_xp} XP added.") 
                st.balloons()
                st.toast("Image Analysis Done") 
                st.rerun() 
            
        except Exception as e: # <-- FIXED: Corrected indentation alignment
            st.error(f"There has been an error when communicating with the AI : {e}")

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

            #code block to render the heatmap
            df_item_heatmap = item.get("heatmap") #retrieves the heatmap stuff 
            if df_item_heatmap is not None and not df_item_heatmap.empty:
                st.markdown("**Global Distribution Heatmap**") #putting a title for the heatmap
                heatmap_chart = pdk.Deck( #setting the charts properties
                    map_style="dark", #allows the map to render properly
                    initial_view_state=pdk.ViewState( 
                        latitude = df_item_heatmap['lat'].mean(), #setting latitude 
                        longitude = df_item_heatmap['lon'].mean(), #setting longitude
                        zoom=1, #setting the zoom
                        pitch=0, #setting the pitch
                    ),
                    layers=[ #making it a heatmap and setting all the stuff up
                        pdk.Layer(
                            "HeatmapLayer", 
                            data=df_item_heatmap,
                            get_position="[lon, lat]" , 
                            opacity = 0.8,
                            radius_pixels=50
                        ),
                    ],
                )
                
                st.pydeck_chart(heatmap_chart) #displaying it 

        st.divider()
else:
    st.info("Nothing has been sent to analyse") # what to show when nothing is there
