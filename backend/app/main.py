from fastapi import FastAPI

app = FastAPI(title="AeroSentinel Backend")

@app.get("/health")
def health():
    return {"status": "ok", "message": "AeroSentinel backend placeholder running"}
