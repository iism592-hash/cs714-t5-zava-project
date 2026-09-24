import os
from openai import OpenAI, AsyncOpenAI

def get_azure_or_openai_client(is_async: bool = False):
    """
    Centralized factory for LLM clients.
    Dynamically routes to Azure OpenAI if keys are present, otherwise defaults to standard OpenAI.
    """
    azure_key = os.getenv("AZURE_OPENAI_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    openai_key = os.getenv("OPENAI_API_KEY")

    if azure_key and azure_endpoint:
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
    return os.getenv("GPT_MODEL_DEPLOYMENT_NAME", "gpt-4o-mini")
