# NPTEL Scraper

A scalable tool that automatically scrapes content for NPTEL MOOC courses and processes the data using Google's Gemini API to generate comprehensive study materials.

## Features

- **Web Scraping**: Automatically scrape NPTEL course content including lectures, transcripts, and course information
- **AI Processing**: Convert lecture transcripts into structured markdown study materials using Gemini AI
- **Configurable**: Centralized configuration management via `config.yaml`
- **Robust Error Handling**: Automatic retry logic with exponential backoff for network requests
- **Logging**: Comprehensive logging system for debugging and monitoring
- **Scalable**: Optimized data structures and efficient string operations for better performance

## Installation

1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your environment variables:
```bash
export GEMINI_API_KEY="your-api-key-here"
```

## Configuration

All settings are managed in `config.yaml`. Key configuration options:

### Course Settings
- `course.url`: NPTEL course URL
- `course.title`: Course identifier

### Execution Control
- `execution.run_scraper`: Enable/disable scraper
- `execution.run_processor`: Enable/disable content processor
- `execution.auto_process_failed`: Auto-process failed lectures

### Scraper Settings
- Timeouts, delays, and retry settings
- Login behavior (automatic vs interactive)

### Processor Settings
- Gemini model versions (flash/pro)
- Safety settings
- Processing mode (transcript/yt)
- Output directories

### Logging
- Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Log format and output file

**Environment Variable Overrides:**
- `NPTEL_COURSE_URL`: Override course URL
- `NPTEL_COURSE_TITLE`: Override course title
- `NPTEL_RUN_SCRAPER`: Override run_scraper setting
- `NPTEL_RUN_PROCESSOR`: Override run_processor setting
- `GEMINI_FLASH_MODEL`: Override flash model version
- `GEMINI_PRO_MODEL`: Override pro model version
- `LOG_LEVEL`: Override log level

## Usage

### Basic Usage
```bash
python main.py
```

The script will:
1. Load configuration from `config.yaml`
2. Optionally scrape the course (if `run_scraper: true`)
3. Process lectures using Gemini AI (if `run_processor: true`)
4. Generate info dumps and study materials

### Configuration Examples

**To scrape and process a new course:**
```yaml
execution:
  run_scraper: true
  run_processor: true
```

**To only process existing scraped data:**
```yaml
execution:
  run_scraper: false
  run_processor: true
```

**To change Gemini models:**
```yaml
processor:
  gemini:
    flash_model: "gemini-2.0-flash-exp"
    pro_model: "gemini-2.0-flash-exp"
```

## Output

- **Scraped Data**: `scrape_results/<course_title>/`
  - `about.txt`: Course description
  - `course_links.json`: All course links organized by week
  - `parsed_lecture_links.json`: YouTube links for lectures
  - `lecture_transcripts/`: VTT transcript files
  - `processed_lectures/`: AI-processed markdown lectures

- **Final Output**: `results/`
  - `info_dumps/<course_title>.txt`: Combined course content
  - `study_materials/<course_title>.md`: Generated study material

## Improvements from Original

- ✅ Removed hardcoded values - now configurable
- ✅ Replaced `print()` statements with proper logging
- ✅ Added comprehensive error handling with retry logic
- ✅ Made interactive login optional (configurable)
- ✅ Optimized string concatenation using `StringIO`
- ✅ Improved data structures (sets for O(1) lookup)
- ✅ Configurable Gemini models and safety settings
- ✅ Centralized configuration management
- ✅ Better code organization and documentation

## License

MIT License