from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

# Your Dynamics 365 credentials
DYNAMICS_URL = "https://org4bb080c9.crm.dynamics.com"
USERNAME = "bhavyamadenurrangegowda@personalaitestingproject.onmicrosoft.com"
PASSWORD = "Buybuy@123"

# Initialize the Chrome WebDriver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

try:
    # Navigate to Dynamics 365
    driver.get(DYNAMICS_URL)
    print("Navigating to Dynamics 365...")
    
    # Wait for Microsoft login page to load
    time.sleep(5)
    
    # Enter username
    username_field = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.NAME, "loginfmt"))
    )
    username_field.send_keys(USERNAME)
    print("Entered username")
    
    # Click Next button
    next_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "idSIButton9"))
    )
    next_button.click()
    print("Clicked Next")
    time.sleep(3)
    
    # Enter password
    password_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "passwd"))
    )
    password_field.send_keys(PASSWORD)
    print("Entered password")
    
    # Click Sign In button
    signin_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "idSIButton9"))
    )
    signin_button.click()
    print("Clicked Sign In - please approve MFA on your phone!")
    
    # Wait for MFA approval
    print("Waiting for MFA approval - please check your phone...")
    time.sleep(30)
    
    # Handle "Stay signed in?" prompt
    try:
        stay_signed_in = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "idSIButton9"))
        )
        stay_signed_in.click()
        print("Clicked Yes on Stay signed in")
        time.sleep(15)
    except:
        print("No Stay signed in prompt found")
    
    # Take a screenshot as proof
    driver.save_screenshot("dynamics_login_success.png")
    print("Screenshot saved!")

except Exception as e:
    print(f"Error: {e}")
    driver.save_screenshot("error_screenshot.png")
    
finally:
    time.sleep(5)
    driver.quit()