import argparse
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="watchdog",
        description="Run one WatchDog server wrapper instance.",
    )
    parser.add_argument(
        "--config",
        default="config/wrapper.yaml",
        help="Path to the WatchDog wrapper config file. Defaults to config/wrapper.yaml.",
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    app = WrapperApp(config_path=args.config)
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
