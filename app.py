import json
import logging
import time
import uuid
from typing import List
import boto3
import jwt
import pymongo
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from odmantic import AIOEngine, ObjectId
from pydantic import UUID4, BaseModel, ByteSize
from starlette.types import Message
from server.config import BaseConfig, Env
from server.database import client
from faire.server.faire_API import run_orders


# get root logger
logger = logging.getLogger(
    __name__
)  # the __name__ resolve to "main" since we are at the root of the project.
# This will get the root logger since no logger in the configuration has this name.

config = BaseConfig()


app = FastAPI()
if not config.mongo_details:
    raise Exception("Environment variables not set.")
engine = AIOEngine(client=client, database=config.database)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """logging middleware"""
    idem = uuid.uuid4()
    logger.info(f"rid={idem} start request path={request.url.path}")
    start_time = time.time()

    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000
    formatted_process_time = "{0:.2f}".format(process_time)
    logger.info(
        f"rid={idem} completed_in={formatted_process_time}ms status_code={response.status_code}"
    )

    return response


async def set_body(request: Request, body: bytes):
    """sets the value of request back to the object after getting the value from the stream object.

    Args:
        request (Request): _description_
        body (bytes): _description_
    """

    async def receive() -> Message:
        return {"type": "http.request", "body": body}

    request._receive = receive


async def get_body(request: Request) -> bytes:
    """allows you to get the body of the request
    while completely avoiding the await hang

    Trying request.body() or request.json() inside of the middleware for FASTAPI will hang.
    https://github.com/tiangolo/fastapi/issues/394#issuecomment-883524819

    Args:
        request (Request): _description_

    Returns:
        bytes: _description_
    """
    body = await request.body()
    # retrieve contents because of stream reader
    # capture contents in a var
    # then set the value in the request object
    await set_body(request, body)
    return body


@app.middleware("http")
async def add_cors_headers(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response


@app.get("/", tags=["Root"])
async def read_root():
    logger.info("logging from the root logger")
    return {"message": "Welcome to this fantastic app!"}


@app.get("/orders")
async def get_orders():
    orders = run_orders()
    return orders