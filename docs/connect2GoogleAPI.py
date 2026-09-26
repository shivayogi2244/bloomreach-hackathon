import os
from dotenv import load_dotenv
from google import genai

# Load environment variables from the .env file
load_dotenv()

# The client automatically picks up GEMINI_API_KEY from your environment
client = genai.Client()

response = client.models.generate_content(
    model="gemini-3.8-flash",
    contents="Hello, Gemini!",
)
print(response.text)
