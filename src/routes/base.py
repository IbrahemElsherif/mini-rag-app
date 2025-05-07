from fastapi import FastAPI, APIRouter, Depends
import os
from helper.config import get_settings, Settings

base_router = APIRouter(
    prefix="/api/v1", #prefix before all routes
    tags=["api_v1"],
)


@base_router.get("/") # Default route used as healthcheck
async def welcome(app_settings: Settings = Depends(get_settings)): # use async for better performance

    app_name = app_settings.APP_NAME
    app_version = app_settings.APP_VERSION
    return {
        "app_name": app_name,
        "app_version": app_version
    } 
