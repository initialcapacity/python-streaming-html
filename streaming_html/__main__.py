import uvicorn

if __name__ == "__main__":
    uvicorn.run("streaming_html.app:create_app", port=8000, reload=True, factory=True)