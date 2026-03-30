"""
Poetry script to run the services
"""

import uvicorn
import argparse


def api():
    parser = argparse.ArgumentParser(description="Run API server")
    parser.add_argument(
        "--local",
        action="store_true",
        help="Run API in local development mode",
    )

    args = parser.parse_args()

    if args.local:
        uvicorn.run(
            "src.main:app",
            host="localhost",
            port=5000,
            reload=True,
        )
    else:
        uvicorn.run(
            "src.main:app",
            host="0.0.0.0",
            port=5000,
        )
