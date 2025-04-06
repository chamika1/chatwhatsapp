import os
import requests
from dotenv import load_dotenv

load_dotenv()

class SinhalaChatbot:
    def __init__(self):
        self.api_key = 'AIzaSyAazWuijnHJB1f4i7MdF5mWyD1MY5moc1U'
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        
    def get_response(self, prompt: str, model: str = "gemini-2.5-pro-exp-03-25") -> str:
        url = f"{self.base_url}/{model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        try:
            response = requests.post(
                url,
                headers={'Content-Type': 'application/json'},
                json=payload
            )
            response.raise_for_status()
            
            # Extract the response text
            response_data = response.json()
            return response_data['candidates'][0]['content']['parts'][0]['text']
            
        except Exception as e:
            return f"API ඉල්ලීම අසාර්ථක: {str(e)}"