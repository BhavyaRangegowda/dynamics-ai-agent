from selenium.webdriver.common.by import By

LOCATOR_LIBRARY = {
    "login_next": [
        (By.ID, "idSIButton9"),
        (By.XPATH, "//input[@type='submit']"),
        (By.XPATH, "//input[@value='Next']"),
        (By.XPATH, "//input[@value='Sign in']"),
    ],

    "new_button": [
        (By.XPATH, "//button[contains(@aria-label,'New')]"),
        (By.XPATH, "//button[contains(@title,'New')]"),
        (By.XPATH, "//button[.//span[normalize-space()='New']]"),
        (By.XPATH, "//*[normalize-space()='New']"),
    ],

    "save_button": [
        (By.XPATH, "//button[contains(@aria-label,'Save')]"),
        (By.XPATH, "//button[contains(@title,'Save')]"),
        (By.XPATH, "//button[@data-id='save_command']"),
        (By.XPATH, "//button[.//span[contains(normalize-space(),'Save')]]"),
    ],

    "qualify_button": [
        (By.XPATH, "//button[contains(@aria-label,'Qualify')]"),
        (By.XPATH, "//button[contains(@title,'Qualify')]"),
        (By.XPATH, "//*[normalize-space()='Qualify']"),
    ],

    "confirm_button": [
        (By.XPATH, "//button[contains(text(),'OK')]"),
        (By.XPATH, "//button[contains(text(),'Yes')]"),
        (By.XPATH, "//button[contains(text(),'Confirm')]"),
        (By.XPATH, "//button[contains(@aria-label,'OK')]"),
    ],

    "search": [
        (By.XPATH, "//input[contains(@placeholder,'Filter by keyword')]"),
        (By.XPATH, "//input[contains(@aria-label,'Filter by keyword')]"),
        (By.XPATH, "//input[contains(@aria-label,'Search')]"),
        (By.CSS_SELECTOR, "input[placeholder*='Filter']"),
        (By.CSS_SELECTOR, "input[aria-label*='Search']"),
    ],

    "topic": [
        (By.XPATH, "//input[@aria-label='Topic']"),
        (By.XPATH, "//input[contains(@data-id,'subject')]"),
        (By.XPATH, "//input[contains(@id,'subject')]"),
        (By.NAME, "subject"),
    ],

    "first_name": [
        (By.XPATH, "//input[@aria-label='First Name']"),
        (By.XPATH, "//input[contains(@data-id,'firstname')]"),
        (By.XPATH, "//input[contains(@id,'firstname')]"),
        (By.NAME, "firstname"),
    ],

    "last_name": [
        (By.XPATH, "//input[@aria-label='Last Name']"),
        (By.XPATH, "//input[contains(@data-id,'lastname')]"),
        (By.XPATH, "//input[contains(@id,'lastname')]"),
        (By.NAME, "lastname"),
    ],

    "company": [
        (By.XPATH, "//input[@aria-label='Company Name']"),
        (By.XPATH, "//input[contains(@data-id,'companyname')]"),
        (By.XPATH, "//input[contains(@id,'companyname')]"),
        (By.NAME, "companyname"),
    ],

    "email": [
        (By.XPATH, "//input[@aria-label='Email']"),
        (By.XPATH, "//input[contains(@data-id,'emailaddress1')]"),
        (By.XPATH, "//input[contains(@id,'emailaddress1')]"),
        (By.NAME, "emailaddress1"),
    ],

    "first_record": [
        (By.XPATH, "(//div[@role='grid']//a)[1]"),
        (By.XPATH, "(//a[contains(@class,'ms-Link')])[1]"),
        (By.XPATH, "(//a[contains(@href,'lead')])[1]"),
        (By.XPATH, "(//a)[1]"),
    ],
}
