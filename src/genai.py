import json
import os

from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY is None:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

gemini_safety_settings=[
    types.SafetySetting(
        category="HARM_CATEGORY_HARASSMENT",
        threshold="BLOCK_NONE",
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_HATE_SPEECH",
        threshold="BLOCK_NONE",
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
        threshold="BLOCK_NONE",
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_DANGEROUS_CONTENT",
        threshold="BLOCK_NONE",
    ),
]
class ContentProcessor:
    def __init__(self, course_title):
        self.scrape_results_dir = "scrape_results"
        self.course_title = course_title
        self.course_about = None
        self.course_content = {}
        self.course_links = {}
        self._init_course_content()
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def _init_course_content(self):
        if not os.path.exists(f"{self.scrape_results_dir}/{self.course_title}"):
            raise ValueError(f"Course content for {self.course_title} does not exist. Please scrape the course first.")  
        with open(f"{self.scrape_results_dir}/{self.course_title}/about.txt", "r", encoding="utf-8") as f:
            self.course_about = f.read()
        with open(f"{self.scrape_results_dir}/{self.course_title}/course_links.json", "r", encoding="utf-8") as f:
            self.course_content = json.load(f)
        with open(f"{self.scrape_results_dir}/{self.course_title}/parsed_lecture_links.json", "r", encoding="utf-8") as f:
            self.course_links = json.load(f)
    
    # free tier on gemini just doesnt wanna work with long videos rn so we go transcript mode
    def _process_one_lecture_yt(self,lecture_name):
        yt_link = self.course_links[lecture_name]
        response = self.client.models.generate_content(
            model="gemini-2.5-flash-preview-04-17",
            config=types.GenerateContentConfig(
            safety_settings=gemini_safety_settings,
            system_instruction="""You will be given a youtube video from a nptel mooc course, the course details and lecture name. 
                Your task is to convert this video into a textual format. Use markdown in a structured manner, use headings, subheadings, code blocks(important!), bullet points, and whatever else necessary.
                - The purpose of this is to make this course accessible to a wider audience. So, make sure to include everything said and done by the instructor in the video.
                """
            ),
            contents=types.Content(
                parts=[
                    types.Part(
                        file_data=types.FileData(file_uri=yt_link)
                    ),
                    types.Part(text=f"""Course Title: {self.course_title}
                        Lecture Name: {lecture_name}
                        Course About: 
                        '''
                        {self.course_about}
                        '''"""
                    )
                ]
            )
        )
        return response.text

    def _process_one_lecture_transcript(self,lecture_name):
        transcript_path = f"{self.scrape_results_dir}/{self.course_title}/lecture_transcripts/{lecture_name}.vtt"
        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript = f.read()
        response = self.client.models.generate_content(
            model="gemini-2.5-flash-preview-04-17",
            config=types.GenerateContentConfig(
            safety_settings=gemini_safety_settings,
            system_instruction="""You will be given a transcript of a youtube video from a nptel mooc course, the course details and lecture name. 
                Your task is to convert this video into a textual format. To do this, follow the instructions below:
                - Use markdown in a structured manner.
                - Use headings, subheadings, code blocks(important!), bullet points, and whatever else necessary.
                - You don't need to include the timestamps in your response.
                - The purpose of this is to make this course accessible to a wider audience. So, make sure to include everything said and done by the instructor in the video.
                - You can make a few assumptions about the content of the video, but don't make any major changes. 
                """
            ),
            contents=types.Content(
                parts=[
                    types.Part(text=f"""Course Title: {self.course_title}
                        Lecture Name: {lecture_name}
                        Course About: 
                        '''
                        {self.course_about}
                        '''
                        ##########################################
                        Transcript:
                        '''
                        {transcript}
                        '''
                        """
                    )
                ]
            )
        )
        return response.text

    def process_one_lecture(self, lecture_name,mode="transcript"):
        os.makedirs(f"{self.scrape_results_dir}/{self.course_title}/processed_lectures", exist_ok=True)
        if mode == "transcript":
            res = self._process_one_lecture_transcript(lecture_name)
        elif mode == "yt":
            res = self._process_one_lecture_yt(lecture_name)
        else:
            raise ValueError("Invalid mode. Use 'transcript' or 'yt'.")
        
        if res is None:
            raise ValueError("Response is None. Your usage quota might be exhausted. Please try again in a few minutes.")

        with open(f"{self.scrape_results_dir}/{self.course_title}/processed_lectures/{lecture_name}.md", "w", encoding="utf-8") as f:
            f.write(res)
            print(f"Processed {lecture_name} and saved to {self.scrape_results_dir}/{self.course_title}/processed_lectures/{lecture_name}.txt")

    def process_all_lectures(self, mode="transcript"):
        os.makedirs(f"{self.scrape_results_dir}/{self.course_title}/processed_lectures", exist_ok=True)
        pre_existing_files = os.listdir(f"{self.scrape_results_dir}/{self.course_title}/processed_lectures")
        all_lectures = self.course_links.keys()
        for lecture_name in all_lectures:
            if f"{lecture_name}.md" in pre_existing_files:
                print(f"{lecture_name} already processed. Skipping...")
                continue
            self.process_one_lecture(lecture_name, mode)
        print(f"\n\n\n\n####################\nProcessed all lectures and saved to {self.scrape_results_dir}/{self.course_title}/processed_lectures/") 

    def generate_final_info_dump(self,auto_process_failed=False):
        os.makedirs(f"{self.scrape_results_dir}/{self.course_title}/processed_lectures", exist_ok=True)
        pre_existing_files = os.listdir(f"{self.scrape_results_dir}/{self.course_title}/processed_lectures")
        all_lectures = self.course_links.keys()
        if len(pre_existing_files) == 0:
            raise ValueError("No processed lectures found. Please process all lectures before generating final info dump.")
            
        for lecture_name in all_lectures:
            if f"{lecture_name}.md" not in pre_existing_files:
                if auto_process_failed:
                    print(f"{lecture_name} not processed. Attempting to process again...")
                    self.process_one_lecture(lecture_name)
                else:
                    raise ValueError(f"{lecture_name} not processed. Please process all lectures before generating final info dump.")
            
        input_text = f"""Course Title: {self.course_title}
Course About:
'''
{self.course_about}
'''
Course Content:
######################"""

        for week in self.course_content:
            week_name = week.replace("_", " ")
            week_name:str = week_name[0].upper() + week_name[1:]
            input_text += f"\n######################\n\n{week_name}\n"
            for lecture_obj in self.course_content[week]["lecture"]:
                lecture_name = lecture_obj[0]
                with open(f"{self.scrape_results_dir}/{self.course_title}/processed_lectures/{lecture_name}.md", "r", encoding="utf-8") as f:
                    process_lecture_content = f.read()
                lecture_name = lecture_name.replace("_", " ")
                lecture_name:str = lecture_name[0].upper() + lecture_name[1:]
                input_text += f"\n\nLecture Name: {lecture_name}\n"
                input_text += f"\n'''\n{process_lecture_content}\n'''\n"
        input_text += "\n\n\n\n####################\nEnd of Course"

        with open(f"{self.scrape_results_dir}/{self.course_title}/{self.course_title}_info_dump.txt", "w", encoding="utf-8") as f:
            f.write(input_text)
            print(f"Processed content and saved to {self.scrape_results_dir}/{self.course_title}/{self.course_title}_info_dump.txt")
        
        os.makedirs(f"results/info_dumps", exist_ok=True)
        with open(f"results/info_dumps/{self.course_title}.txt", "w", encoding="utf-8") as f:
            f.write(input_text)

    def generate_study_material(self):
        if not os.path.exists(f"{self.scrape_results_dir}/{self.course_title}/{self.course_title}_info_dump.txt"):
            raise ValueError("No info dump found. Please generate the info dump before generating study material.")
        
        with open("prompt.md", "r", encoding="utf-8") as f:
            prompt = f.read()
        
        with open(f"{self.scrape_results_dir}/{self.course_title}/{self.course_title}_info_dump.txt", "r", encoding="utf-8") as f:
            info_dump = f.read()

        response = self.client.models.generate_content(
            model="gemini-2.5-pro-exp-03-25",
            config=types.GenerateContentConfig(
                safety_settings=gemini_safety_settings,
                system_instruction=prompt),
            contents=types.Content(
                parts=[
                    types.Part(text=info_dump),
                ]
            )
        )
        with open(f"{self.scrape_results_dir}/{self.course_title}/{self.course_title}_study_material.md", "w", encoding="utf-8") as f:
            f.write(response.text)
            print(f"Processed content and saved to {self.scrape_results_dir}/{self.course_title}/{self.course_title}_study_material.md")
        print("Study material generated successfully.")

        os.makedirs(f"results/study_materials", exist_ok=True)
        with open(f"results/study_materials/{self.course_title}.md", "w", encoding="utf-8") as f:
            f.write(response.text)