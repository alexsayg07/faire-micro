import os
from pydantic import BaseSettings
from enum import Enum
from dotenv.main import load_dotenv


class Env(str, Enum):
    prod = "prod"
    dev = "dev"


class BaseConfig(BaseSettings):
    # mongo
    load_dotenv()
    mongo_details: str = os.getenv("MONGO_DETAILS")
    database: str = "faire-data"

    dev_aws_access_key: str = os.getenv("DEV_AWS_ACCESS_KEY")
    dev_aws_secret_access_key: str = os.getenv("DEV_SECRET_ACCESS_KEY")

    # faire
    # Define the API endpoint and key
    faire_url = "https://www.faire.com/external-api/v2"
    faire_api_key: str = os.getenv("X-FAIRE-ACCESS-TOKEN")

    # Set up authentication headers
    faire_auth_headers = {
        "Content-Type": "application/json",
        "X-FAIRE-ACCESS-TOKEN": faire_api_key,
    }

    # * INTEGRATIONS
    slack_api_key: str = ""

    environment: Env = os.getenv("ENV", "dev")
