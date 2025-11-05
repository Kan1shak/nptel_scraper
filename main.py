import logging
from src.scraper import NPTELScraper
from src.genai import ContentProcessor
from src.config import Config

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    config = Config()

    # Example: Full pipeline - scrape and process
    if config.run_scraper:
        logger.info(f"Starting scraper for course: {config.course_url}")
        scraper = NPTELScraper(config.course_url, config)
        scraper.get_course_about()
        scraper.get_course_lecture_links()
        scraper.parse_lecture_links()
        course_title = scraper.course_title
    else:
        course_title = config.course_title

    # Process content with ContentProcessor
    if config.run_processor:
        logger.info(f"Starting content processor for: {course_title}")
        processor = ContentProcessor(course_title, config)
        processor.generate_final_info_dump(auto_process_failed=config.auto_process_failed)

if __name__ == "__main__":
    main()