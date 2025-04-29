import os
import json
from seleniumbase import Driver

class NPTELScraper:
    def __init__(self, course_url):
        self.user_data_dir = "nptel_user"
        self.scrape_results_dir = "scrape_results"
        self.course_url = course_url
        self.swayam_url = "https://swayam.gov.in/wso?redirect=/"
        self.sb:Driver = Driver(uc=True,locale="en", ad_block=True, user_data_dir=self.user_data_dir)
        self.check_login()

    def google_login(self):
        print("Logging in with Google...")
        selector = "#GoogleExchange"
        self.sb.click_if_visible(selector, by="css selector", timeout=3)
        self.sb.sleep(5)
        if self.sb.is_element_present('input[type="email"]', by="css selector") or self.sb.is_element_present('[data-authuser="-1"]', by="css selector"):
            input("You have not logged into your google account.\nPlease login to a google account in a *NEW TAB* and press Enter to continue...")
            self.check_login()
        else:
            print("Already logged in to Google.")
        
        # check if the google login was successful
        if self.sb.is_element_present('[class="user-profile-dropdown"', by="css selector"):
            print("Logged in successfully.")
        else:
            print("Login failed. Please check your credentials.")
            raise Exception("Login failed.")
        
    def check_login(self):
        print("Checking login status...")
        self.sb.open(self.swayam_url)
        self.sb.sleep(5)
        selector = ".accountButton"
        if self.sb.is_element_present(selector, by="css selector"):
            print("Not logged in. Trying logging in with google.")
            self.google_login()
        else:
            print("Logged in successfully. Now redirecting to course page.")

    def get_course_about(self):
        print("Getting course about...")
        self.sb.open(self.course_url)
        course_title = self.sb.get_text(".gcb-product-headers-large", by="css selector")
        course_title = course_title.lower().replace(" ", "_")
        self.course_title = course_title
        course_content = self.sb.get_text("#gcb-content", by="css selector")

        os.makedirs(f"{self.scrape_results_dir}/{course_title}", exist_ok=True)

        with open(f"{self.scrape_results_dir}/{course_title}/about.txt", "w", encoding="utf-8") as f:
            f.write(course_content)
            print("Course about content saved to file.")

    def get_course_lecture_links(self):
        print("Getting course lecture links...")
        self.sb.open(self.course_url)
        week_elements = self.sb.find_elements(".unit_heading")
        week_elements = [week.get_attribute("id") for week in week_elements]
        weeks = [
            week
            for week in week_elements 
            if "Week" in self.sb.get_text(f"#{week}") 
        ]
        content = {}
        for week in weeks:
            # click the week so its visible
            self.sb.click(f"#{week}")
            week_name = self.sb.get_text(f"#{week}")
            week_name = week_name.lower().replace(" ", "_")
            week_selector = f"#{week.replace("heading", "navbar")} .subunit_other a"
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
                elif "materials" in link_name:
                    week_content_schema["material"].append(link_content)
                elif "lecture" in link_name:
                    week_content_schema["lecture"].append(link_content)
                elif "quiz" in link_name:
                    week_content_schema["assignment"].append(link_content)
            content[week_name] = week_content_schema

        os.makedirs(f"{self.scrape_results_dir}/{self.course_title}", exist_ok=True)
        with open(f"{self.scrape_results_dir}/{self.course_title}/course_links.json", "w", encoding="utf-8") as f:
            json.dump(content, f, indent=4)
            print("Course lecture links saved to file.")

    def __exit__(self, exc_type, exc_value, traceback):
        self.sb.quit()