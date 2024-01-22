import motor.motor_asyncio
from odmantic import AIOEngine
from faire.server.config import BaseConfig

config = BaseConfig()
MONGO_DETAILS = config.mongo_details

try:
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DETAILS)

except ConnectionError:
    print("USING LOCAL!!")
    client = motor.motor_asyncio.AsyncIOMotorClient(
       "mongodb+srv://czero:<password>@faire-data.r6pe0wu.mongodb.net/?retryWrites=true&w=majority")
engine = AIOEngine(client=client, database=config.database)
database = "faire-data"