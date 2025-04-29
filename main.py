from src.scraper import NPTELScraper

def main():
    course_url = "https://onlinecourses.nptel.ac.in/noc25_mg45/course"
    scraper = NPTELScraper(course_url)
    scraper.get_course_about()
    scraper.get_course_lecture_links()
    scraper.parse_lecture_links()

main()