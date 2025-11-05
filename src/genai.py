import json
import logging
import os
from io import StringIO
from typing import Optional

from google import genai
from google.genai import types
from src.config import Config

logger = logging.getLogger(__name__)

# Get API key from environment
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY is None:
    raise ValueError("GEMINI_API_KEY environment variable not set.")


class ContentProcessor:
    def __init__(self, course_title: str, config: Optional[Config] = None):
        """
        Initialize Content Processor for generating study materials.

        Args:
            course_title: Title of the course to process
            config: Configuration object. If None, loads default config.
        """
        self.config = config if config else Config()
        self.course_title = course_title
        self.scrape_results_dir = self.config.scrape_results_dir
        self.course_about = None
        self.course_content = {}
        self.course_links = {}

        logger.info(f"Initializing ContentProcessor for: {course_title}")
        self._init_course_content()
        self.client = genai.Client(api_key=GEMINI_API_KEY)

        # Build safety settings from config
        self._safety_settings = self._build_safety_settings()

    def _build_safety_settings(self):
        """Build Gemini safety settings from configuration"""
        safety_config = self.config.safety_settings
        return [
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold=safety_config["harassment"],
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH",
                threshold=safety_config["hate_speech"],
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold=safety_config["sexually_explicit"],
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold=safety_config["dangerous_content"],
            ),
        ]

    def _init_course_content(self):
        """Load course content from scraped files"""
        course_dir = f"{self.scrape_results_dir}/{self.course_title}"

        if not os.path.exists(course_dir):
            raise ValueError(
                f"Course content for '{self.course_title}' does not exist at {course_dir}. "
                "Please scrape the course first."
            )

        try:
            # Load course about
            about_path = f"{course_dir}/about.txt"
            with open(about_path, "r", encoding="utf-8") as f:
                self.course_about = f.read()
            logger.debug(f"Loaded course about from: {about_path}")

            # Load course links
            links_path = f"{course_dir}/course_links.json"
            with open(links_path, "r", encoding="utf-8") as f:
                self.course_content = json.load(f)
            logger.debug(f"Loaded course links from: {links_path}")

            # Load parsed lecture links
            parsed_path = f"{course_dir}/parsed_lecture_links.json"
            with open(parsed_path, "r", encoding="utf-8") as f:
                self.course_links = json.load(f)
            logger.info(f"Loaded {len(self.course_links)} lecture links")

        except FileNotFoundError as e:
            logger.error(f"Required file not found: {e}")
            raise ValueError(
                f"Missing required file for course '{self.course_title}'. "
                "Please ensure the course has been fully scraped."
            )
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in course files: {e}")
            raise
    
    def _process_one_lecture_yt(self, lecture_name: str) -> Optional[str]:
        """
        Process a lecture using YouTube video (requires higher API tier).

        Args:
            lecture_name: Name of the lecture to process

        Returns:
            Processed content as markdown string, or None if failed
        """
        yt_link = self.course_links[lecture_name]
        logger.debug(f"Processing lecture via YouTube: {lecture_name}")

        try:
            response = self.client.models.generate_content(
                model=self.config.flash_model,
                config=types.GenerateContentConfig(
                    safety_settings=self._safety_settings,
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
        except Exception as e:
            logger.error(f"Error processing lecture '{lecture_name}' via YouTube: {e}")
            return None

    def _process_one_lecture_transcript(self, lecture_name: str) -> Optional[str]:
        """
        Process a lecture using transcript (more reliable for free tier).

        Args:
            lecture_name: Name of the lecture to process

        Returns:
            Processed content as markdown string, or None if failed
        """
        transcript_path = f"{self.scrape_results_dir}/{self.course_title}/lecture_transcripts/{lecture_name}.vtt"
        logger.debug(f"Processing lecture via transcript: {lecture_name}")

        try:
            with open(transcript_path, "r", encoding="utf-8") as f:
                transcript = f.read()

            response = self.client.models.generate_content(
                model=self.config.flash_model,
                config=types.GenerateContentConfig(
                    safety_settings=self._safety_settings,
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
        except FileNotFoundError:
            logger.error(f"Transcript file not found for: {lecture_name}")
            return None
        except Exception as e:
            logger.error(f"Error processing lecture '{lecture_name}' via transcript: {e}")
            return None

    def process_one_lecture(self, lecture_name: str, mode: str = "transcript"):
        """
        Process a single lecture and save to markdown file.

        Args:
            lecture_name: Name of the lecture to process
            mode: Processing mode - 'transcript' or 'yt'
        """
        processed_dir = f"{self.scrape_results_dir}/{self.course_title}/processed_lectures"
        os.makedirs(processed_dir, exist_ok=True)

        logger.info(f"Processing lecture: {lecture_name} (mode: {mode})")

        if mode == "transcript":
            res = self._process_one_lecture_transcript(lecture_name)
        elif mode == "yt":
            res = self._process_one_lecture_yt(lecture_name)
        else:
            raise ValueError(f"Invalid mode: {mode}. Use 'transcript' or 'yt'.")

        if res is None:
            error_msg = (
                f"Failed to process lecture '{lecture_name}'. "
                "This might be due to API quota limits or network issues."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        output_path = f"{processed_dir}/{lecture_name}.md"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(res)
        logger.info(f"Saved processed lecture to: {output_path}")

    def process_all_lectures(self, mode: str = "transcript"):
        """
        Process all lectures in the course.

        Args:
            mode: Processing mode - 'transcript' or 'yt'
        """
        processed_dir = f"{self.scrape_results_dir}/{self.course_title}/processed_lectures"
        os.makedirs(processed_dir, exist_ok=True)

        # Use set for O(1) lookup performance
        pre_existing_files = set(os.listdir(processed_dir))
        all_lectures = list(self.course_links.keys())

        logger.info(f"Processing {len(all_lectures)} lectures (mode: {mode})")
        processed_count = 0
        skipped_count = 0

        for lecture_name in all_lectures:
            if f"{lecture_name}.md" in pre_existing_files:
                logger.debug(f"Skipping already processed: {lecture_name}")
                skipped_count += 1
                continue

            try:
                self.process_one_lecture(lecture_name, mode)
                processed_count += 1
            except Exception as e:
                logger.error(f"Failed to process {lecture_name}: {e}")

        logger.info(
            f"Lecture processing complete. Processed: {processed_count}, "
            f"Skipped: {skipped_count}, Total: {len(all_lectures)}"
        ) 

    def generate_final_info_dump(self, auto_process_failed: bool = False):
        """
        Generate final info dump by combining all processed lectures.

        Args:
            auto_process_failed: If True, automatically process missing lectures
        """
        logger.info("Generating final info dump...")
        processed_dir = f"{self.scrape_results_dir}/{self.course_title}/processed_lectures"
        os.makedirs(processed_dir, exist_ok=True)

        # Use set for O(1) lookup
        pre_existing_files = set(os.listdir(processed_dir))
        all_lectures = list(self.course_links.keys())

        if len(pre_existing_files) == 0:
            raise ValueError(
                "No processed lectures found. Please process all lectures "
                "before generating final info dump."
            )

        # Check for missing lectures
        for lecture_name in all_lectures:
            if f"{lecture_name}.md" not in pre_existing_files:
                if auto_process_failed:
                    logger.info(f"Processing missing lecture: {lecture_name}")
                    try:
                        self.process_one_lecture(lecture_name, mode=self.config.processing_mode)
                    except Exception as e:
                        logger.error(f"Failed to process {lecture_name}: {e}")
                        raise
                else:
                    raise ValueError(
                        f"Lecture '{lecture_name}' not processed. "
                        "Set auto_process_failed=True to process missing lectures automatically."
                    )

        # Build info dump using StringIO for better performance
        logger.debug("Building info dump content...")
        output = StringIO()
        output.write(f"""Course Title: {self.course_title}
Course About:
'''
{self.course_about}
'''
Course Content:
######################""")

        for week in self.course_content:
            week_name = week.replace("_", " ")
            week_name = week_name[0].upper() + week_name[1:]
            output.write(f"\n######################\n\n{week_name}\n")

            for lecture_obj in self.course_content[week]["lecture"]:
                lecture_name = lecture_obj[0]
                lecture_path = f"{processed_dir}/{lecture_name}.md"

                with open(lecture_path, "r", encoding="utf-8") as f:
                    process_lecture_content = f.read()

                formatted_name = lecture_name.replace("_", " ")
                formatted_name = formatted_name[0].upper() + formatted_name[1:]
                output.write(f"\n\nLecture Name: {formatted_name}\n")
                output.write(f"\n'''\n{process_lecture_content}\n'''\n")

        output.write("\n\n\n\n####################\nEnd of Course")
        input_text = output.getvalue()

        # Save to course directory
        course_dump_path = f"{self.scrape_results_dir}/{self.course_title}/{self.course_title}_info_dump.txt"
        with open(course_dump_path, "w", encoding="utf-8") as f:
            f.write(input_text)
        logger.info(f"Info dump saved to: {course_dump_path}")

        # Save to results directory
        os.makedirs(self.config.info_dumps_dir, exist_ok=True)
        results_dump_path = f"{self.config.info_dumps_dir}/{self.course_title}.txt"
        with open(results_dump_path, "w", encoding="utf-8") as f:
            f.write(input_text)
        logger.info(f"Info dump also saved to: {results_dump_path}")

    def generate_study_material(self):
        """Generate comprehensive study material from info dump using Gemini Pro"""
        logger.info("Generating study material...")

        info_dump_path = f"{self.scrape_results_dir}/{self.course_title}/{self.course_title}_info_dump.txt"
        if not os.path.exists(info_dump_path):
            raise ValueError(
                "No info dump found. Please generate the info dump "
                "before generating study material."
            )

        # Load prompt template
        try:
            with open("prompt.md", "r", encoding="utf-8") as f:
                prompt = f.read()
        except FileNotFoundError:
            logger.warning("prompt.md not found, using default prompt")
            prompt = "Generate comprehensive study material from the provided course content."

        # Load info dump
        with open(info_dump_path, "r", encoding="utf-8") as f:
            info_dump = f.read()

        logger.debug(f"Using model: {self.config.pro_model}")

        try:
            response = self.client.models.generate_content(
                model=self.config.pro_model,
                config=types.GenerateContentConfig(
                    safety_settings=self._safety_settings,
                    system_instruction=prompt
                ),
                contents=types.Content(
                    parts=[
                        types.Part(text=info_dump),
                    ]
                )
            )

            # Save to course directory
            course_material_path = f"{self.scrape_results_dir}/{self.course_title}/{self.course_title}_study_material.md"
            with open(course_material_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            logger.info(f"Study material saved to: {course_material_path}")

            # Save to results directory
            os.makedirs(self.config.study_materials_dir, exist_ok=True)
            results_material_path = f"{self.config.study_materials_dir}/{self.course_title}.md"
            with open(results_material_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            logger.info(f"Study material also saved to: {results_material_path}")

        except Exception as e:
            logger.error(f"Error generating study material: {e}")
            raise