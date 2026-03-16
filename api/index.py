# Vercel サーバーレス関数のエントリーポイント
# vercel.json の rewrites により全リクエストがここに転送される
from api.main import app  # noqa: F401
