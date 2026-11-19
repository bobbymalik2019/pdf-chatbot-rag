from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .auth import router as auth_router
from .oauth import router as oauth_router

app = FastAPI(title='SSO Identity Service', docs_url='/docs', redoc_url='/redoc')
app.include_router(auth_router)
app.include_router(oauth_router)

@app.get('/healthz')
def healthz():
    return {'status': 'ok', 'service': 'sso'}

@app.middleware('http')
async def harden(request: Request, call_next):
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response
