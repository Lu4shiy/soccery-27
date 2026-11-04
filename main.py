from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Soccery 27 server is running!"}