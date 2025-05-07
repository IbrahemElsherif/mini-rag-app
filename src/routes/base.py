from fastapi import FastAPI, APIRouter, Depends, Request
import os
from helper.config import get_settings, Settings
from models.ProjectModel import ProjectModel
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

@base_router.get("/projects")
async def list_projects(request: Request):
    project_model = await ProjectModel().create_instance(
        db_client=request.app.db_client
    )
    
    projects, _ = await project_model.get_all_projects(page=1, page_size=100)
    
    return {
        "projects": [
            {"project_id": project.project_id}
            for project in projects
        ]
    }