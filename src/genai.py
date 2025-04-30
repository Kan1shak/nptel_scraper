import json
import os

from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY is None:
    raise ValueError("GEMINI_API_KEY environment variable not set.")
client = genai.Client(api_key=GEMINI_API_KEY)


class ContentProcessor:
    def __init__(self, course_title):
        self.scrape_results_dir = "scrape_results"
        self.course_title = course_title
        self.course_about = None
        self.course_content = {}
        self.course_links = {}
        self.init_course_content()

    def init_course_content(self):
        if not os.path.exists(f"{self.scrape_results_dir}/{self.course_title}"):
            raise ValueError(f"Course content for {self.course_title} does not exist. Please scrape the course first.")  
        with open(f"{self.scrape_results_dir}/{self.course_title}/about.txt", "r", encoding="utf-8") as f:
            self.course_about = f.read()
        with open(f"{self.scrape_results_dir}/{self.course_title}/course_links.json", "r", encoding="utf-8") as f:
            self.course_content = json.load(f)
        with open(f"{self.scrape_results_dir}/{self.course_title}/parsed_lecture_links.json", "r", encoding="utf-8") as f:
            self.course_links = json.load(f)

    def process_one_lecture(self, lecture_name):
        yt_link = self.course_links[lecture_name]
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-04-17",
            config=types.GenerateContentConfig(
            safety_settings=[
                        types.SafetySetting(
                            category="HARM_CATEGORY_HARASSMENT",
                            threshold="BLOCK_NONE",  # Block none
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_HATE_SPEECH",
                            threshold="BLOCK_NONE",  # Block none
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                            threshold="BLOCK_NONE",  # Block none
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_DANGEROUS_CONTENT",
                            threshold="BLOCK_NONE",  # Block none
                        ),
            ],
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
        print(response.text)

        os.makedirs(f"{self.scrape_results_dir}/{self.course_title}/processed_lectures", exist_ok=True)

        with open(f"{self.scrape_results_dir}/{self.course_title}/processed_lectures/{lecture_name}.txt", "w", encoding="utf-8") as f:
            f.write(response.text)
            print(f"\n\n\n\n##################################\nLecture {lecture_name} processed and saved to file.")