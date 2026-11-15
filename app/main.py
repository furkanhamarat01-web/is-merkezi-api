from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import cors_origins
from app.db import init_db
from app.endpoints import contacts, dashboard, health, invoices, offers, projects, reminders, reports, settings, store, talepler, tasks, transactions


@asynccontextmanager
async def lifespan(_app):
    init_db()
    yield


app = FastAPI(title="VKV İş Takip Merkezi API", version="1.0.0", lifespan=lifespan)
origins = cors_origins()
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health.router)
app.include_router(dashboard.router)
app.include_router(tasks.router)
app.include_router(projects.router)
app.include_router(invoices.router)
app.include_router(reminders.router)
app.include_router(contacts.router)
app.include_router(transactions.router)
app.include_router(offers.router)
app.include_router(talepler.router)
app.include_router(reports.router)
app.include_router(settings.router)
app.include_router(store.router)
