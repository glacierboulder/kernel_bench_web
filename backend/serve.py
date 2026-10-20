"""Start the web service using CLI > environment > JSON config > defaults."""
import argparse


def main() -> None:
    parser=argparse.ArgumentParser(description="Start the local agent benchmark web service")
    parser.add_argument("--host")
    parser.add_argument("--port",type=int)
    args=parser.parse_args()
    from .settings import load_settings
    settings=load_settings(overrides={"host":args.host,"port":args.port})
    import uvicorn
    uvicorn.run("backend.app:app",host=settings.host,port=settings.port,
                log_level="warning",workers=1)


if __name__ == "__main__":
    main()
