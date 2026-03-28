from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

service = Service(executable_path='chromedriver.exe')
driver = webdriver.Chrome(service = service)

driver.get('https://www.youtube.com')

# In case of slow internet connection
WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CLASS_NAME, "ytSearchboxComponentInput"))
)

input_element = driver.find_element(By.CLASS_NAME, "ytSearchboxComponentInput") #Find by inspect element
input_element.clear()
input_element.send_keys('Lamoon' + Keys.ENTER)

#First link in the page

wait = WebDriverWait(driver, 15)

video = wait.until(
    EC.element_to_be_clickable((
        By.XPATH,
        "//a[@id='video-title' and contains(@aria-label, 'LAMOON')]"
    ))
)
video.click()

time.sleep(5)

driver.quit()
