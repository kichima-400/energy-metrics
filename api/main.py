"""
エネルギー価格相関ダッシュボード - FastAPI バックエンド

起動方法:
  uvicorn api.main:app --reload --port 8000

APIドキュメント:
  http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers.data import router as data_router

app = FastAPI(
    title="エネルギー価格相関ダッシュボード API",
    description="原油・LNG・石炭・為替・国内エネルギー価格の時系列データを提供する。",
    version="0.1.0",
)

# Next.js からのリクエストを許可（ローカル開発 + Vercel 本番）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.vercel.app",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(data_router)


@app.get("/health")
def health():
    return {"status": "ok"}
