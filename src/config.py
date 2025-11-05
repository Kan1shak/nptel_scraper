import os
import yaml
from pathlib import Path
from typing import Optional

class Config:
    """Configuration manager for NPTEL Scraper"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration from YAML file.

        Args:
            config_path: Path to config.yaml file. If None, looks in project root.
        """
        if config_path is None:
            # Look for config.yaml in project root
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config.yaml"

        self.config_path = Path(config_path)
        self._load_config()
        self._validate_config()

    def _load_config(self):
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}\n"
                "Please create a config.yaml file in the project root."
            )

        with open(self.config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)

    def _validate_config(self):
        """Validate required configuration fields"""
        required_sections = ['course', 'execution', 'scraper', 'processor', 'logging']
        for section in required_sections:
            if section not in self._config:
                raise ValueError(f"Missing required configuration section: {section}")

    # Course settings
    @property
    def course_url(self) -> str:
        return os.environ.get('NPTEL_COURSE_URL', self._config['course']['url'])

    @property
    def course_title(self) -> str:
        return os.environ.get('NPTEL_COURSE_TITLE', self._config['course']['title'])

    # Execution control
    @property
    def run_scraper(self) -> bool:
        return os.environ.get('NPTEL_RUN_SCRAPER', str(self._config['execution']['run_scraper'])).lower() == 'true'

    @property
    def run_processor(self) -> bool:
        return os.environ.get('NPTEL_RUN_PROCESSOR', str(self._config['execution']['run_processor'])).lower() == 'true'

    @property
    def auto_process_failed(self) -> bool:
        return self._config['execution']['auto_process_failed']

    # Scraper settings
    @property
    def user_data_dir(self) -> str:
        return self._config['scraper']['user_data_dir']

    @property
    def scrape_results_dir(self) -> str:
        return self._config['scraper']['scrape_results_dir']

    @property
    def swayam_url(self) -> str:
        return self._config['scraper']['swayam_url']

    @property
    def click_timeout(self) -> int:
        return self._config['scraper']['click_timeout']

    @property
    def page_load_delay(self) -> int:
        return self._config['scraper']['page_load_delay']

    @property
    def auto_login(self) -> bool:
        return self._config['scraper']['auto_login']

    @property
    def interactive_login(self) -> bool:
        return self._config['scraper']['interactive_login']

    @property
    def request_timeout(self) -> int:
        return self._config['scraper']['request_timeout']

    @property
    def max_retries(self) -> int:
        return self._config['scraper']['max_retries']

    @property
    def retry_backoff_factor(self) -> int:
        return self._config['scraper']['retry_backoff_factor']

    # Processor settings
    @property
    def flash_model(self) -> str:
        return os.environ.get('GEMINI_FLASH_MODEL', self._config['processor']['gemini']['flash_model'])

    @property
    def pro_model(self) -> str:
        return os.environ.get('GEMINI_PRO_MODEL', self._config['processor']['gemini']['pro_model'])

    @property
    def safety_settings(self) -> dict:
        return self._config['processor']['gemini']['safety']

    @property
    def processing_mode(self) -> str:
        return self._config['processor']['processing_mode']

    @property
    def results_dir(self) -> str:
        return self._config['processor']['results_dir']

    @property
    def info_dumps_dir(self) -> str:
        return self._config['processor']['info_dumps_dir']

    @property
    def study_materials_dir(self) -> str:
        return self._config['processor']['study_materials_dir']

    # Logging settings
    @property
    def log_level(self) -> str:
        return os.environ.get('LOG_LEVEL', self._config['logging']['level'])

    @property
    def log_format(self) -> str:
        return self._config['logging']['format']

    @property
    def log_file(self) -> Optional[str]:
        return self._config['logging']['file']

    def get(self, key: str, default=None):
        """Get a configuration value by key with dot notation (e.g., 'course.url')"""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
