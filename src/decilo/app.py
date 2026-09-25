"""Punto de entrada de la aplicacion Decilo (backend)."""

from fastapi import FastAPI

app = FastAPI(title="Decilo")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
