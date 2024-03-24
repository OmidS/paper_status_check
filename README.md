# Paper Status
During the long process of peer review, getting any signal about the progress of the review at the journal is great. Manuscript tracking systems fortunately show the status of the paper to some extent... unfortunately, not all status messages stay in the log of the manuscript tracking system so if you don't check the system regularly, you may miss them. This repository is just an automation code to check that status of submissions for Nature journals. 

The code uses Selenium to log in and check the manuscript tracking system, and keeps a csv log of the status for each under review manuscript associated with the account. You can have your system scheduler run this every day to have an idea of how the submission status changed over time.

These may depend on the journal and submission round, but some status states include:
- Manuscript data ready
- Manuscript to editorial office (pending quality check)
- Editor assigned
- Manuscript under consideration
- All Reviewers Assigned
- Editor Decision Started
- Manuscript under editorial consideration


## Setup
### Python
Create a new virtual environment:
```sh
python -m venv c:\envs\paper_status_check
```

Install `requirements.txt` in the python virtual environment:
```sh
pip install -r requirements.txt
```

### Web drivers
Install Chrome or Firefox and download the driver for controlling them by Selenium. 

Firefox seems to work better for the Nature manuscript tracking website website.

If you use a chrome driver, every time chrome is updated make sure you download the correct chromedriver.exe from https://googlechromelabs.github.io/chrome-for-testing/#stable and replace the old one. Otherwise the tweeting will fail.

### Environment variables
Create a `.env` file next to paper_status_check.py and populate the following environment variables based on your account on the journal system and your system: 
```sh
NATURE_USERNAME="YOUR_USER_NAME"
NATURE_PASSWORD="YOUR_PASSWORD"
SELENIUM_DRIVER="firefox"
SELENIUM_HEADLESS=true
SELENIUM_WAIT="30"
FIREFOX_DRIVER_PATH="path\to\geckodriver.exe"
CHROME_DRIVER_PATH="path\to\chromedriver.exe"
CHROME_USER_DATA_DIR="path\to\chromedriver_user_data"
CHROME_PROFILE="Auto"
LOG_LEVEL="DEBUG"
```

Username and password are for your account on https://mts-nn.nature.com/cgi-bin/main.plex?form_type=home

### Scheduling a job
Schedule a job on your system to run `paper_status_check.py` with the frequency that you like. 

You would need a script that activates the virtual environment and then calls `paper_status_check.py`. 

For Windows, `update.bat` does this. Edit as needed with the appropriate virtual environment path. 

The Task Scheduler on Windows can take a command and an interval to run it. The task should be to run `update.bat` with the desired frequency (e.g., every morning).