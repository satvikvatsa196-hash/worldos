from fastapi import FastAPI

app = FastAPI(title="WORLDOS", description="Autonomous persistent world simulation powered by agentic AI")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "WORLDOS"}
