from src.scraper import NPTELScraper
from src.genai import ContentProcessor

def main():
    # set the course URL for scraping
    # make sure to include the course url with the `/course` suffix
    course_url = "https://onlinecourses.nptel.ac.in/noc25_mg45/course"
    # initialize the scraper with the course URL
    scraper = NPTELScraper(course_url)
    # scrape the course page
    scraper.get_course_about()
    # get the course content links
    scraper.get_course_lecture_links()
    # parse the links to get lecture content
    scraper.parse_lecture_links()

    # initialize the content processor with the course title
    processor = ContentProcessor(scraper.course_title)
    # process all lectures to generate textual info dump
    processor.process_all_lectures()

if __name__ == "__main__":
    main()