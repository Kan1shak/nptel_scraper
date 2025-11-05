import json
import logging
import os
import re
import time
from typing import Optional
import requests

from seleniumbase import Driver
from src.config import Config

logger = logging.getLogger(__name__)

class NPTELScraper:
    def __init__(self, course_url: str, config: Optional[Config] = None):
        """
        Initialize NPTEL Scraper.

        Args:
            course_url: URL of the NPTEL course to scrape
            config: Configuration object. If None, loads default config.
        """
        self.config = config if config else Config()
        self.course_url = course_url
        self.user_data_dir = self.config.user_data_dir
        self.scrape_results_dir = self.config.scrape_results_dir
        self.swayam_url = self.config.swayam_url

        logger.info(f"Initializing NPTEL Scraper for: {course_url}")
        self.sb: Driver = Driver(
            uc=True,
            locale="en",
            ad_block=True,
            user_data_dir=self.user_data_dir
        )
        self.check_login()

    def google_login(self):
        """Attempt to login with Google"""
        logger.info("Attempting to login with Google...")
        selector = "#GoogleExchange"
        self.sb.click_if_visible(selector, by="css selector", timeout=self.config.click_timeout)
        self.sb.sleep(self.config.page_load_delay)

        # Check if login is required
        needs_login = (
            self.sb.is_element_present('input[type="email"]', by="css selector") or
            self.sb.is_element_present('[data-authuser="-1"]', by="css selector")
        )

        if needs_login:
            if self.config.interactive_login:
                logger.warning("Manual login required.")
                input("Please login to Google in a NEW TAB and press Enter to continue...")
                self.check_login()
            else:
                logger.error("Login required but interactive_login is disabled in config")
                raise Exception(
                    "Login required. Please set 'interactive_login: true' in config.yaml "
                    "or login manually before running the scraper."
                )
        else:
            logger.info("Already logged in to Google")

        # Verify login was successful
        if self.sb.is_element_present('[class="user-profile-dropdown"', by="css selector"):
            logger.info("Login successful")
        else:
            logger.error("Login failed - could not find user profile dropdown")
            raise Exception("Login failed. Please check your credentials.")

    def check_login(self):
        """Check if user is logged in and attempt login if needed"""
        logger.info("Checking login status...")
        try:
            self.sb.open(self.swayam_url)
            self.sb.sleep(self.config.page_load_delay)
            selector = ".accountButton"

            if self.sb.is_element_present(selector, by="css selector"):
                if self.config.auto_login:
                    logger.info("Not logged in. Attempting automatic login...")
                    self.google_login()
                else:
                    logger.error("Not logged in and auto_login is disabled")
                    raise Exception(
                        "Not logged in. Please set 'auto_login: true' in config.yaml "
                        "or login manually before running."
                    )
            else:
                logger.info("Already logged in. Redirecting to course page.")
        except Exception as e:
            logger.error(f"Error during login check: {e}")
            raise

    def get_course_about(self):
        """Scrape course about/description page"""
        logger.info("Fetching course about information...")
        try:
            self.sb.open(self.course_url)
            course_title = self.sb.get_text(".gcb-product-headers-large", by="css selector")
            course_title = course_title.lower().replace(" ", "_")
            self.course_title = course_title
            logger.info(f"Course title: {course_title}")

            course_content = self.sb.get_text("#gcb-content", by="css selector")

            # Create directory
            course_dir = f"{self.scrape_results_dir}/{course_title}"
            os.makedirs(course_dir, exist_ok=True)

            # Save about content
            about_path = f"{course_dir}/about.txt"
            with open(about_path, "w", encoding="utf-8") as f:
                f.write(course_content)
            logger.info(f"Course about content saved to: {about_path}")

        except Exception as e:
            logger.error(f"Error fetching course about: {e}")
            raise

    def get_course_lecture_links(self):
        """Scrape all course lecture links organized by week"""
        logger.info("Fetching course lecture links...")
        try:
            self.sb.open(self.course_url)
            week_elements = self.sb.find_elements(".unit_heading")
            week_elements = [week.get_attribute("id") for week in week_elements]
            weeks = [
                week
                for week in week_elements
                if "Week" in self.sb.get_text(f"#{week}")
            ]
            logger.info(f"Found {len(weeks)} weeks")

            content = {}
            for week in weeks:
                # Click the week to make it visible
                self.sb.click(f"#{week}")
                week_name = self.sb.get_text(f"#{week}")
                week_name = week_name.lower().replace(" ", "_")
                logger.debug(f"Processing {week_name}")

                week_selector = f"#{week.replace('heading', 'navbar')} .subunit_other a"
                week_content = self.sb.find_elements(week_selector)
                week_content = [link.get_attribute("id") for link in week_content]

                week_content_schema = {
                    "practice_quiz": [],
                    "lecture": [],
                    "assignment": [],
                    "material": [],
                }

                for link in week_content:
                    link_name = self.sb.get_text(f"#{link}")
                    link_name = link_name.lower().replace(" ", "_")
                    link_href = self.sb.get_attribute(f"#{link}", "href")
                    link_content = (link_name, link_href)

                    if "practice" in link_name:
                        week_content_schema["practice_quiz"].append(link_content)
                    elif "material" in link_name:
                        week_content_schema["material"].append(link_content)
                    elif "lecture" in link_name:
                        week_content_schema["lecture"].append(link_content)
                    elif "quiz" in link_name:
                        week_content_schema["assignment"].append(link_content)

                content[week_name] = week_content_schema
                logger.debug(f"{week_name}: {len(week_content_schema['lecture'])} lectures")

            # Save to file
            course_dir = f"{self.scrape_results_dir}/{self.course_title}"
            os.makedirs(course_dir, exist_ok=True)
            links_path = f"{course_dir}/course_links.json"

            with open(links_path, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=4)
            logger.info(f"Course lecture links saved to: {links_path}")

        except Exception as e:
            logger.error(f"Error fetching course lecture links: {e}")
            raise

    def _make_request_with_retry(self, url: str, **kwargs) -> Optional[requests.Response]:
        """
        Make HTTP request with exponential backoff retry logic.

        Args:
            url: URL to request
            **kwargs: Additional arguments for requests.get()

        Returns:
            Response object or None if all retries failed
        """
        kwargs.setdefault('timeout', self.config.request_timeout)

        for attempt in range(self.config.max_retries):
            try:
                response = requests.get(url, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                wait_time = self.config.retry_backoff_factor ** attempt
                if attempt < self.config.max_retries - 1:
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{self.config.max_retries}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Request failed after {self.config.max_retries} attempts: {e}")
                    return None

    def parse_lecture_links(self):
        """Parse lecture links to extract YouTube video IDs and transcripts"""
        logger.info("Parsing lecture links...")
        try:
            # Load course links
            links_path = f"{self.scrape_results_dir}/{self.course_title}/course_links.json"
            with open(links_path, "r", encoding="utf-8") as f:
                content = json.load(f)

            # Create transcript directory
            transcript_dir = f"{self.scrape_results_dir}/{self.course_title}/lecture_transcripts"
            os.makedirs(transcript_dir, exist_ok=True)

            # Get cookies for authenticated requests
            self.sb.open(self.course_url)
            cookie_g_a = self.sb.get_cookie("g_a")
            cookie_g_a = cookie_g_a["value"] if cookie_g_a else None
            cookie_g_b = self.sb.get_cookie("g_b")
            cookie_g_b = cookie_g_b["value"] if cookie_g_b else None

            cookies = {"g_a": cookie_g_a, "g_b": cookie_g_b}
            parsed_lecture_links = {}
            failed_lectures = []

            for week, week_content in content.items():
                for content_type, links in week_content.items():
                    if content_type == "lecture":
                        for link in links:
                            link_name, link_href = tuple(link)
                            logger.debug(f"Parsing: {link_name}")

                            # Fetch lecture page
                            response = self._make_request_with_retry(link_href, cookies=cookies)
                            if not response or response.status_code != 200:
                                logger.error(f"Failed to fetch lecture page: {link_name}")
                                failed_lectures.append(link_name)
                                continue

                            response_text = response.text

                            # Extract YouTube video ID
                            pattern = r"loadIFramePlayer\(\s*['\"]([A-Za-z0-9_-]{11})(?=['\"]\s*,)"
                            vid_id_match = re.search(pattern, response_text)

                            if not vid_id_match:
                                logger.warning(f"Could not extract video ID for: {link_name}")
                                failed_lectures.append(link_name)
                                continue

                            yt_link = f"https://www.youtube.com/watch?v={vid_id_match.group(1)}"
                            parsed_lecture_links[link_name] = yt_link
                            logger.info(f"Parsed: {link_name} -> {yt_link}")

                            # Extract and download transcript
                            transcript_pattern = r'<option value="">Select Language </option>\s*<\s*option[^>]*value="([^"]+)(?=")'
                            transcript_match = re.search(transcript_pattern, response_text)

                            if not transcript_match:
                                logger.warning(f"No transcript found for: {link_name}")
                                continue

                            transcript_url = f"https://onlinecourses.nptel.ac.in/course/subtitle?url={transcript_match.group(1)}"
                            transcript_response = self._make_request_with_retry(transcript_url)

                            if transcript_response and transcript_response.status_code == 200:
                                transcript_vtt = transcript_response.text.replace("WEBVTT", "")
                                transcript_path = f"{transcript_dir}/{link_name}.vtt"
                                with open(transcript_path, "w", encoding="utf-8") as f:
                                    f.write(transcript_vtt)
                                logger.debug(f"Transcript saved: {link_name}")
                            else:
                                logger.warning(f"Failed to download transcript for: {link_name}")

            # Save parsed lecture links
            parsed_links_path = f"{self.scrape_results_dir}/{self.course_title}/parsed_lecture_links.json"
            with open(parsed_links_path, "w", encoding="utf-8") as f:
                json.dump(parsed_lecture_links, f, indent=4)

            logger.info(f"Parsed {len(parsed_lecture_links)} lectures successfully")
            if failed_lectures:
                logger.warning(f"Failed to parse {len(failed_lectures)} lectures: {failed_lectures}")

        except Exception as e:
            logger.error(f"Error parsing lecture links: {e}")
            raise

    def __exit__(self, exc_type, exc_value, traceback):
        self.sb.quit()