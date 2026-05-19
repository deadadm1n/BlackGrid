import asyncio
import sys

try:
    from wrapper.core.app import WrapperApp
except ModuleNotFoundError as exc:
    missing = exc.name or str(exc)
    print(
        f"Missing Python package: {missing}\n"
        "Install the wrapper requirements with:\n"
        f'  "{sys.executable}" -m pip install -r requirements.txt',
        file=sys.stderr,
    )
    raise SystemExit(1) from exc

async def main():
    app = WrapperApp()
    await app.run()

if __name__ == "__main__":
    asyncio.run(main())
