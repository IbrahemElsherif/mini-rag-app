from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from routes import base, data, nlp
from helper.config import get_settings
from stores.llm.LLMProviderFactory import LLMProviderFactory
from stores.vectordb.VectorDBProviderFactory import VectorDBProviderFactory
from stores.llm.templatess.template_parser import TemplateParser

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # أو حدد دومين موقعك بدل النجمة
    allow_credentials=True,
    allow_methods=["*"],  # لازم تكون فيها "OPTIONS"
    allow_headers=["*"],
)


async def startup_span():
    settings = get_settings()

    # stay visible to the routes
    app.mongo_conn = AsyncIOMotorClient(settings.MONGODB_URL)
    app.db_client = app.mongo_conn[settings.MONGODB_DATABASE]

    # create instance of factory
    llm_provider_factory = LLMProviderFactory(settings)
    vectordb_provider_factory = VectorDBProviderFactory(settings)

    # generation client
    app.generation_client = llm_provider_factory.create(provider=settings.GENERATION_BACKEND)
    app.generation_client.set_generation_model(model_id = settings.GENERATION_MODEL_ID)

    # embedding client
    app.embedding_client = llm_provider_factory.create(provider=settings.EMBEDDING_BACKEND)
    app.embedding_client.set_embedding_model(model_id=settings.EMBEDDING_MODEL_ID,
                                            embedding_size=settings.EMBEDDING_MODEL_SIZE)
    
    # vector db client
    app.vectordb_client = vectordb_provider_factory.create(
        provider=settings.VECTOR_DB_BACKEND
    )
    app.vectordb_client.connect()

    app.template_parser = TemplateParser(
        language=settings.PRIMARY_LANG,
        default_language=settings.DEFAULT_LANG,
    )

async def shutdown_span():
    app.mongo_conn.close()
    app.vectordb_client.disconnect()

# app.router.lifespan.on_startup.append(startup_span)
# app.router.lifespan.on_shutdown.append(shutdown_span)

app.on_event("startup")(startup_span)
app.on_event("shutdown")(shutdown_span)


app.include_router(base.base_router)
app.include_router(data.data_router)
app.include_router(nlp.nlp_router)
