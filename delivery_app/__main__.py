"""Run the delivery app with `python -m delivery_app`."""

import os

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "delivery_app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )

