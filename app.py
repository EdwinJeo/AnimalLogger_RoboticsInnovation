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
from supabase import create_client, Client
from streamlit_geolocation import streamlit_geolocation
from dotenv import load_dotenv

load_dotenv()

#supabase api stuff
SUPABASE_URL = os.environ.get("SUPABASE_URL") #this is so that it knows where to put stuff 
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") #this is so that it can put stuff 
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


#Getting the page set up so that the tab thingy shows stuff 
st.set_page_config(page_title="Talos Wildlife Recogniser", page_icon="🌿")
st.title("Talos Wildlife Recogniser 🌿")

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

#getting real-world GPS coordinates for field logging
st.markdown("**Location Access**")
st.write("Click below to allow GPS location for scientific logging purposes")
loc = streamlit_geolocation()

#the actual picture thing
picture = st.camera_input("Take a photo of an animal or plant for me to analyse")

#to give the picture to ai i need to check i havent already done it
if picture and picture != st.session_state.last_processed:
    #sets the picture taken to a variable to ensure it doesn't get processed again 
    st.session_state.last_processed = picture

    #cool spinning animation to show smth happening
    with st.spinner("We are currently processing wildlife and global databases... "):

        prompt = """Analyze this image. It could contain animals, plants, trees, or flowers. If there are multiple subjects present, list each one separately. Provide the response for each subject in this exact format:
        Name: [Common name of the animal or plant, e.g., Oak Tree, Red Fox]
        Endangerment: [Conservation status or plant status e.g., Least Concern, Endangered, Common Cultivated]
        Population: [Brief detail about its global population or growing range]
        Eco-Fact: [One short, kid-friendly fact on how it helps the ecosystem or environment]
        XP: [Give it an XP score between 50 and 200 based on how rare or interesting it is, just write the number]
        GlobalPoints: [Provide 6 to 10 pairs of latitude and longitude coordinates representing its worldwide habitat or native regions, formatted strictly as: lat,lon; lat,lon; lat,lon]

        If there are multiple subjects, separate each block with '---' on its own line.
        Please note that if the image does not show an animal or plant then respond with 'No Wildlife Identified'
        """

        #give the image to the ai 
        try:
            response = client.models.generate_content(
                model= 'gemini-3.5-flash-lite' , 
                contents=[Image.open(picture),prompt]
            )

            ai_description = response.text #uses the variable to make it easier

            if "No Wildlife Identified" in ai_description: #this way if it detects nothing it wont store or give xp 
                st.warning("No animal or plant was detected in this photo, please take another photo") #to give user warning 
            else: #any other time just respond with this
                animal_blocks = ai_description.split("---") #splitting it like this means we can process multiple animals in one image as long as AI can recognise them 
                total_earned_xp = 0  #using a variable for the entire picture that way it all gets added at once 
                
                for block in animal_blocks: #just so that it goes through each block and does this code instead. this helps with support for multi animals
                    if not block.strip():
                        continue

                    earned_xp = 100 #default fallback for the thing as the other stuff wont always work 
                    for line in block.split('\n'): #sorts through the response line by line
                        if "XP:" in line: #find the word xp within line so that it knows where to search 
                            nums = re.findall(r'\d+',line ) #setting a variable to the xp value - but it is string 
                            if nums: #to get the xp into the xp score thing
                                earned_xp = int(nums[0]) #adds the parsed xp score to the earned xp thingy


                    subject_name = "Wildlife" #making a default fallback in case of fail
                    for line in block.split('\n'):#sorts through ai response line by line 
                        if "Name:" in line: #identifies part with the name in it 
                            subject_name = line.replace("Name:" , "").strip() # replaces variable with the name 


                    #getting the data for heatmap to work
                    heatmap_data = [] #getting the heatmap data into index / list
                    clean_description_lines = [] #so that this way the user doesn't see anything
                    for line in block.split('\n'): #parsing through all of the lines
                        if "GlobalPoints:" in line: #searching for the lat and long
                            points_str = line.replace("GlobalPoints:", "").strip() #setting into variable
                            pairs = points_str.split(';') #splitting into pairs by splitting after the semi colon
                            for pair in pairs: #for every pair in the pairs thing then do smth else
                                if ',' in pair: #if there is a comma in the pair then
                                    try:  # do this 
                                        lat_str, lon_str = pair.split(',') #split into two variables which are lat and long 
                                        heatmap_data.append({"lat": float(lat_str.strip()), "lon": float(lon_str.strip() )}) #set it to the index or list and do it by setting this through use of float and strip to cut it 
                                    except ValueError: #if there is something wrong then pass code
                                        pass
                        else:
                            clean_description_lines.append(line) #if doesnt work then just delete that line from the thing

                    clean_description = "\n".join(clean_description_lines) #removing that line to make it nice and clean for end user
                    formatted_description = clean_description.replace('\n',  '  \n') #replacing it with better new line as that new line is not accepted in md 
                    df_heatmap = pd.DataFrame(heatmap_data) #variable called data for heatmap is set up

                    image_url = None# image url is set to none to act as a fallback 
                    try:
                        formatted_query = urllib.parse.quote(subject_name) #sets a variable to give to the url as the animal/plant name 
                        wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{formatted_query}" #gets the image using the name that we just got 
                        headers = {'User-Agent': 'TalosWildlifeRecogniser/1.0 (Educational Project)'} #to follow the strict wikimedia guidelines

                        wiki_response = requests.get(wiki_url, headers = headers) #asking wikimedia for the picture 
                        if wiki_response.status_code == 200: #if it says yes then set the data into a file 
                            wiki_data = wiki_response.json() #setting data into a file
                            if "thumbnail" in wiki_data: #checking to see if there is a pic 
                                image_url = wiki_data["thumbnail"]["source"] #setting the image url for the pic 
                    except Exception: #if not work then dont do 
                        pass

                    #fallback if this doesn't work 
                    display_image = image_url if image_url else Image.open(picture)

                    # SUPABASE STORAGE UPLOAD & DATABASE SYNC FOR SCIENTISTS
                    stored_image_url = None
                    try:
                        picture_bytes = picture.getvalue() #gets the actual picture 
                        file_name = f"{datetime.now().timestamp()}_{subject_name.replace(' ', '_')}.jpg" #puts a custom filename ensuring nothing gets overwritten
                        
                        supabase.storage.from_("wildlife-photos").upload( #uplaoding stuff and listing all the parameters
                            path=file_name, #this means file name 
                            file=picture_bytes, #what the actual file is 
                            file_options={"content-type": "image/jpeg"} #what the filetype is 
                        )
                        stored_image_url = supabase.storage.from_("wildlife-photos").get_public_url(file_name) #getting yet another fallback for the history thing
                    except Exception as storage_err: #if there is error logic
                        print(f"Storage upload error: {storage_err}") #display error 
                        stored_image_url = image_url # Fallback URL if storage upload fails

                    # Extract real user GPS coordinates (fallback to London/UK coordinates if geolocation hasn't loaded yet)
                    user_lat = loc.get('latitude') if loc and loc.get('latitude') is not None else 51.5074
                    user_lon = loc.get('longitude') if loc and loc.get('longitude') is not None else -0.1278

                    # Insert observation record into Supabase Database table using real GPS location
                    try:
                        supabase.table("observations").insert({
                            "species_name": subject_name,
                            "latitude": user_lat,
                            "longitude": user_lon,
                            "image_url": stored_image_url
                        }).execute()
                    except Exception as db_err: #error logic
                        print(f"Database insert error: {db_err}")

                    total_earned_xp += earned_xp

                    analysed_items = {
                        "image" : display_image,
                        "description" : f"{formatted_description}  \n\n  {earned_xp} XP",
                        "heatmap" : df_heatmap #because history log shows all of them we need to make sure they each save theirs
                    }

                    st.session_state.history.insert(0, analysed_items) #puts into the list at the bottom

                st.session_state.score += total_earned_xp
                st.success(f"Successfully processed wildlife! Logged to Global Database. Total +{total_earned_xp} XP added.") #displays the response in a green text box
                st.balloons()
                st.toast("Image Analysis & Database Sync Done") #just to say it worked

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
