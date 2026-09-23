"""
test_live_azure_llm.py
=============================================================================
Live test script to verify communication with your deployed Azure AI model.
=============================================================================
"""

import os
import sys
from dotenv import load_dotenv

# Reconfigure console encoding for Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")
load_dotenv()

ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://iism592-2225-resource.services.ai.azure.com/openai/v1")
MODEL_NAME = os.getenv("GPT_MODEL_DEPLOYMENT_NAME", "gpt-5.4-nano")
API_KEY = os.getenv("AZURE_OPENAI_KEY", "").strip()

print("=" * 65)
print(" TESTING LIVE AZURE AI MODEL CONNECTION")
print(f" Target Endpoint: {ENDPOINT}")
print(f" Deployment:      {MODEL_NAME}")
print("=" * 65)

try:
    from openai import OpenAI

    # If an API Key is provided in .env, use it directly
    if API_KEY:
        print("\n>> Authenticating using: Azure API Key")
        client = OpenAI(
            base_url=ENDPOINT,
            api_key=API_KEY
        )
    else:
        # Otherwise, authenticate using Azure Entra ID Token Provider
        print("\n>> Authenticating using: DefaultAzureCredential (Token Provider)")
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider
        
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(), 
            "https://ai.azure.com/.default"
        )
        
        # In modern Azure AI Services, token is passed via bearer token or api_version
        from openai import AzureOpenAI
        # Check if endpoint contains azure.com
        base_endpoint = ENDPOINT.replace("/openai/v1", "").rstrip("/")
        client = AzureOpenAI(
            azure_endpoint=base_endpoint,
            azure_ad_token_provider=token_provider,
            api_version="2024-05-01-preview"
        )

    print(f"\n>> Sending test prompt to '{MODEL_NAME}'...")
    
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are the AI assistant for Zava DIY Hardware store."},
            {"role": "user", "content": "Hello! Introduce yourself in one sentence and tell me what you do."}
        ],
        max_completion_tokens=100
    )

    print("\n" + "-" * 65)
    print("📢 RESPONSE RECEIVED FROM YOUR LIVE MODEL:")
    print("-" * 65)
    print(response.choices[0].message.content)
    print("-" * 65)
    print("\n✅ SUCCESS: Your Azure AI model is LIVE and responding to Python!")

except Exception as e:
    print("\n❌ Error connecting to model:")
    print(str(e))
    print("\nTips:")
    print("1. If using Token Provider, make sure you ran 'az login' in your terminal.")
    print("2. If you have an API Key, paste it into AZURE_OPENAI_KEY in your .env file.")
