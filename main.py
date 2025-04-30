from src.scraper import NPTELScraper
from src.genai import ContentProcessor

def main():
    # course_url = "https://onlinecourses.nptel.ac.in/noc25_mg45/course"
    # scraper = NPTELScraper(course_url)
    # scraper.get_course_about()
    # scraper.get_course_lecture_links()
    # scraper.parse_lecture_links()
    course_title = "marketing_analytics"
    lecture_name = "lecture_1:_introduction_to_r_programming"
    processor = ContentProcessor(course_title)
    processor.process_one_lecture(lecture_name)

if __name__ == "__main__":
    main()