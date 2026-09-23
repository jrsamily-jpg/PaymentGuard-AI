# ruff: noqa: B008
# FastAPI dependencies are intentionally declared in endpoint signatures.
"""Authenticated workspace API. Owner identity comes exclusively from bearer sessions."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.risk_engine.rules import catalog
from app.workspace import auth, service
from app.workspace.database import Session, initialize
from app.workspace.schemas import (
    CaseChange,
    CaseInput,
    Credentials,
    PaymentBatch,
    SimulationRequest,
)


@asynccontextmanager
async def lifespan(app):
    initialize()
    yield


app = FastAPI(
    title="PaymentGuard",
    version="2.0.0",
    description="User-isolated payment-event analysis. No payment processor is connected. No preloaded activity.",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, error: RequestValidationError):
    # FastAPI's default validation response can echo passwords and other inputs.
    details = [
        {"loc": item["loc"], "msg": item["msg"], "type": item["type"]}
        for item in error.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": details})


bearer = HTTPBearer(auto_error=False)


def db():
    with Session() as session:
        yield session


def user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session=Depends(db),
):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Sign in to continue.")
    try:
        return auth.authenticate(session, credentials.credentials)
    except auth.AuthenticationError as error:
        raise HTTPException(401, str(error)) from error


def run(action):
    try:
        return action()
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(409, str(error)) from error


@app.middleware("http")
async def bounded_request(request: Request, call_next):
    size = request.headers.get("content-length")
    if size and (not size.isdigit() or int(size) > 5_000_000):
        return JSONResponse(
            status_code=413, content={"detail": "Request is too large."}
        )
    # Bound actual bytes too, including requests without Content-Length.
    chunks = []
    received = 0
    async for chunk in request.stream():
        received += len(chunk)
        if received > 5_000_000:
            return JSONResponse(
                status_code=413, content={"detail": "Request is too large."}
            )
        chunks.append(chunk)
    request._body = b"".join(chunks)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/health")
def health():
    return {"status": "ok", "mode": "workspace", "payment_processor_connected": False}


@app.post("/auth/register", status_code=201)
def register(data: Credentials, session=Depends(db)):
    return run(lambda: auth.register(session, data))


@app.post("/auth/login")
def login(data: Credentials, session=Depends(db)):
    try:
        return auth.login(session, data)
    except auth.AuthenticationError as error:
        raise HTTPException(401, str(error)) from error


@app.post("/auth/logout")
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    owner=Depends(user),
    session=Depends(db),
):
    auth.logout(session, credentials.credentials)
    return {"signed_out": True}


@app.get("/auth/me")
def me(owner=Depends(user)):
    return owner


@app.get("/transactions")
def transactions(
    owner=Depends(user),
    session=Depends(db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return service.event_page(session, owner["id"], limit, offset)


@app.post("/transactions/import", status_code=201)
def ingest(batch: PaymentBatch, owner=Depends(user), session=Depends(db)):
    return run(lambda: service.ingest(session, owner["id"], batch.payments))


@app.get("/transactions/{payment_id}")
def payment(payment_id: str, owner=Depends(user), session=Depends(db)):
    return run(lambda: service.payment(session, owner["id"], payment_id))


@app.get("/transactions/{payment_id}/explanation")
def explanation(payment_id: str, owner=Depends(user), session=Depends(db)):
    row = run(lambda: service.payment(session, owner["id"], payment_id))
    return {
        "score": row["score"],
        "signals": row["signals"],
        "evaluated_rules": row["evaluated_rules"],
        "method": "Rules-only; missing evidence is unknown, not safe.",
    }


@app.get("/analytics/summary")
def summary(owner=Depends(user), session=Depends(db)):
    return service.summary(
        service.events(session, owner["id"]), service.cases(session, owner["id"])
    )


@app.get("/analytics/rails")
def rails(owner=Depends(user), session=Depends(db)):
    return service.rail_analysis(session, owner["id"])


@app.get("/rules")
def rules(owner=Depends(user)):
    return catalog()


@app.get("/rules/performance")
def performance(owner=Depends(user), session=Depends(db)):
    return service.rule_performance(service.events(session, owner["id"]))


@app.post("/rules/simulate")
def simulate(request: SimulationRequest, owner=Depends(user), session=Depends(db)):
    return run(lambda: service.simulate(service.events(session, owner["id"]), request))


@app.get("/cases")
def cases(owner=Depends(user), session=Depends(db)):
    return service.cases(session, owner["id"])


@app.post("/cases", status_code=201)
def create_case(data: CaseInput, owner=Depends(user), session=Depends(db)):
    return run(lambda: service.create_case(session, owner["id"], data.payment_id))


@app.patch("/cases/{case_id}")
def update_case(
    case_id: str, data: CaseChange, owner=Depends(user), session=Depends(db)
):
    return run(lambda: service.update_case(session, owner["id"], case_id, data))


@app.get("/audit")
def audit(owner=Depends(user), session=Depends(db)):
    return service.audit(session, owner["id"])


@app.get("/models/performance")
def models(owner=Depends(user)):
    return {
        "status": "not_evaluated",
        "metrics": None,
        "message": "No model has been trained or evaluated on this workspace's data.",
    }


@app.get("/reports/risk", response_class=HTMLResponse)
def report(owner=Depends(user), session=Depends(db)):
    return service.report(
        service.events(session, owner["id"]), service.cases(session, owner["id"])
    )
