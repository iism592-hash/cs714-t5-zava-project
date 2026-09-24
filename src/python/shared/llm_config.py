import os
from openai import OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI
from azure.identity import AzureCliCredential, get_bearer_token_provider

def get_azure_or_openai_client(is_async: bool = False):
    """
    Centralized factory for LLM clients.
    Supports Azure AI Project (Keyless), Standard Azure OpenAI (Keys), or standard OpenAI.
    """
    ai_project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    azure_key = os.getenv("AZURE_OPENAI_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    openai_key = os.getenv("OPENAI_API_KEY")

    if ai_project_endpoint:
        token_provider = get_bearer_token_provider(
            AzureCliCredential(), "https://cognitiveservices.azure.com/.default"
        )
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        if is_async:
            return AsyncAzureOpenAI(azure_ad_token_provider=token_provider, api_version=api_version, azure_endpoint=ai_project_endpoint)
        else:
            return AzureOpenAI(azure_ad_token_provider=token_provider, api_version=api_version, azure_endpoint=ai_project_endpoint)
            
    elif azure_key and azure_endpoint:
        if is_async:
            return AsyncOpenAI(base_url=azure_endpoint, api_key=azure_key)
        else:
            return OpenAI(base_url=azure_endpoint, api_key=azure_key)
    else:
        if is_async:
            return AsyncOpenAI(api_key=openai_key)
        else:
            return OpenAI(api_key=openai_key)

def get_model_name() -> str:
    """Returns the correct model deployment name for the current environment."""
    return os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", os.getenv("GPT_MODEL_DEPLOYMENT_NAME", "gpt-4o-mini"))
