import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
import random
import os
from dotenv import load_dotenv
import requests
import re

class LinkedInConnector:
    def __init__(self, headless: bool = False):
        load_dotenv()
        self.email = os.getenv('LINKEDIN_EMAIL')
        self.password = os.getenv('LINKEDIN_PASSWORD')
        
        if not self.email or not self.password:
            raise ValueError("LinkedIn credentials not found in .env file")
        
        self.driver = None
        self.wait = None
        self.headless = headless
    
    def setup_driver(self):
        """Initialize Chrome WebDriver with updated configuration"""
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--disable-notifications')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 10)
        
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    def clean_text(self, text):
        """Remove emoji and non-BMP characters from text"""
        # Remove emoji and other non-BMP characters
        cleaned_text = re.sub(r'[^\u0000-\uFFFF]', '', text)
        # Remove multiple spaces
        cleaned_text = ' '.join(cleaned_text.split())
        return cleaned_text

    def generate_connection_note(self, profile_data):
        """Generate personalized connection note using Ollama"""
        try:
            prompt = f"""Generate a brief, professional LinkedIn connection note for {profile_data['name']}, 
            who is a {profile_data['current_position']}. Keep it under 200 characters. 
            Do not include any emojis or special characters and just give the output message that can be directly pasted there."""
            
            url = 'http://localhost:11434/api/generate'
            data = {
                'model': 'llama2',
                'prompt': prompt,
                'stream': False
            }
            
            response = requests.post(url, json=data)
            
            if response.status_code == 200:
                note = response.json().get('response', '').strip()
                # Clean the text and ensure it's within LinkedIn's character limit
                cleaned_note = self.clean_text(note)
                if len(cleaned_note) > 200:
                    print(f"Warning: Generated note length ({len(cleaned_note)}) exceeds limit. Truncating...")
                return cleaned_note[:200]
            else:
                print(f"Error from Ollama API: {response.text}")
                return "Hi, I'd love to connect and expand our professional network."
                
        except Exception as e:
            print(f"Error generating connection note: {str(e)}")
            return "Hi, I'd love to connect and expand our professional network."

    def login(self):
        """Log into LinkedIn with improved error handling"""
        try:
            print("Logging into LinkedIn...")
            self.driver.get('https://www.linkedin.com/login')
            time.sleep(2)
            
            print("Entering email...")
            email_field = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
            email_field.send_keys(self.email)
            
            print("Entering password...")
            password_field = self.wait.until(EC.presence_of_element_located((By.ID, "password")))
            password_field.send_keys(self.password)
            
            print("Clicking login button...")
            login_button = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
            login_button.click()
            
            time.sleep(5)
            
            if "feed" in self.driver.current_url or "mynetwork" in self.driver.current_url:
                print("Successfully logged in!")
                return True
            else:
                print("Login may have failed. Current URL:", self.driver.current_url)
                return False
            
        except Exception as e:
            print(f"Login failed: {str(e)}")
            return False

    def click_button_safely(self, button, action_name):
        """Helper method to safely click buttons with retries"""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                if button.is_displayed() and button.is_enabled():
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                    time.sleep(1)
                    self.driver.execute_script("arguments[0].click();", button)
                    print(f"Successfully clicked {action_name} button")
                    return True
            except Exception as e:
                print(f"Attempt {attempt + 1} failed to click {action_name} button: {str(e)}")
                if attempt < max_attempts - 1:
                    time.sleep(2)
                    continue
        return False

    def find_and_click_send_button(self):
        """Helper method to find and click the send button using multiple selectors"""
        possible_selectors = [
            "button[aria-label*='Send now']",
            "button[aria-label*='send']",
            "button[type='submit']",
            "button.artdeco-button--primary",
            ".artdeco-modal__confirm-dialog-btn"
        ]
        
        for selector in possible_selectors:
            try:
                buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for button in buttons:
                    try:
                        button_text = button.text.lower()
                        if 'send' in button_text or 'done' in button_text:
                            if self.click_button_safely(button, "Send"):
                                return True
                    except:
                        continue
            except:
                continue
        return False
    
    def connect_with_profile(self, profile_url, profile_data):
        """Connect with a single profile and send connection note"""
        try:
            if not profile_url.startswith('http'):
                profile_url = f"https://{profile_url}"
            
            print(f"Navigating to profile: {profile_url}")
            self.driver.get(profile_url)
            time.sleep(5)
            
            # Find and click Connect button
            print("Looking for Connect button...")
            connect_buttons = self.driver.find_elements(By.CSS_SELECTOR, 
                "button[aria-label*='Connect'], button[aria-label*='connect']")
            
            if connect_buttons:
                print(f"Found {len(connect_buttons)} potential connect buttons")
                for button in connect_buttons:
                    try:
                        if not self.click_button_safely(button, "Connect"):
                            continue
                            
                        # Add longer wait after clicking connect
                        time.sleep(3)
                        
                        # Handle the Add Note dialog
                        try:
                            print("Looking for 'Add a note' button...")
                            # Updated selector to be more comprehensive
                            add_note_buttons = self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 
                                "button[aria-label*='Add a note'], button[aria-label*='note'], button.artdeco-button--secondary")))
                            
                            add_note_clicked = False
                            for add_note_button in add_note_buttons:
                                try:
                                    button_text = add_note_button.text.lower()
                                    if 'note' in button_text or 'message' in button_text:
                                        if self.click_button_safely(add_note_button, "Add note"):
                                            add_note_clicked = True
                                            break
                                except:
                                    continue
                                    
                            if not add_note_clicked:
                                print("Could not click Add note button")
                                continue
                            
                            # Add longer wait after clicking add note
                            time.sleep(2)
                            
                            # Generate and enter connection note
                            print("Generating connection note...")
                            note = self.generate_connection_note(profile_data)
                            print(f"Generated note ({len(note)} chars): {note}")
                            
                            # Enhanced textarea handling with explicit waits
                            possible_textareas = [
                                "textarea#custom-message",
                                "textarea.send-invite__custom-message",
                                "textarea[name='message']",
                                "textarea.connect-button-send-invite__custom-message",
                                "textarea[aria-label*='message']",
                                "textarea.artdeco-text-input--input"
                            ]
                            
                            textarea_found = False
                            for selector in possible_textareas:
                                try:
                                    # Use explicit wait for textarea
                                    note_field = self.wait.until(
                                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                                    )
                                    
                                    # Ensure element is interactive
                                    self.wait.until(
                                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                                    )
                                    
                                    print(f"Found textarea using selector: {selector}")
                                    
                                    # Scroll textarea into view
                                    self.driver.execute_script(
                                        "arguments[0].scrollIntoView({block: 'center'});", 
                                        note_field
                                    )
                                    time.sleep(1)
                                    
                                    # Clear and enter text using JavaScript
                                    self.driver.execute_script(
                                        "arguments[0].value = arguments[1];", 
                                        note_field, 
                                        note
                                    )
                                    
                                    # Trigger input event to ensure LinkedIn registers the change
                                    self.driver.execute_script(
                                        """
                                        var event = new Event('input', {
                                            bubbles: true,
                                            cancelable: true,
                                        });
                                        arguments[0].dispatchEvent(event);
                                        """, 
                                        note_field
                                    )
                                    
                                    textarea_found = True
                                    break
                                except Exception as e:
                                    print(f"Failed with selector {selector}: {str(e)}")
                                    continue
                            
                            if not textarea_found:
                                print("Could not find note textarea")
                                continue
                            
                            time.sleep(2)
                            
                            # Try to click the send button with improved handling
                            print("Attempting to click send button...")
                            if self.find_and_click_send_button():
                                print("Successfully clicked send button")
                                time.sleep(2)
                                return True
                            
                            print("Failed to click send button")
                            return False
                                
                        except TimeoutException as e:
                            print(f"Timeout while handling note dialog: {str(e)}")
                            continue
                            
                        except Exception as e:
                            print(f"Error while handling note dialog: {str(e)}")
                            continue
                            
                    except Exception as e:
                        print(f"Error with connect button: {str(e)}")
                        continue
            
            print("Could not find or click Connect button")
            return False
            
        except Exception as e:
            print(f"Error connecting with profile: {str(e)}")
            return False
    
    def run(self, profile_file: str):
        """Main execution method"""
        try:
            self.setup_driver()
            if not self.login():
                print("Login failed. Exiting...")
                return
            
            with open(profile_file, 'r') as f:
                profiles = json.load(f)
            
            for profile in profiles:
                print(f"\nProcessing profile: {profile['name']}")
                if self.connect_with_profile(profile['url'], profile):
                    print(f"Successfully processed {profile['name']}")
                else:
                    print(f"Failed to process {profile['name']}")
                
                delay = random.uniform(20, 40)
                print(f"Waiting {delay:.0f} seconds before next profile...")
                time.sleep(delay)
                
        except Exception as e:
            print(f"Error during execution: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
                print("Browser closed.")

def main():
    connector = LinkedInConnector(headless=False)
    connector.run("profile_data.json")

if __name__ == "__main__":
    main()
