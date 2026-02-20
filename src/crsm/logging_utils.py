import logging

from rich.logging import RichHandler


def configure_logging(verbose: int = 0) -> None:
    level = logging.WARNING
    if verbose == 1:
        level = logging.INFO
    elif verbose >= 2:
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False, show_time=False)],
    )

    # Silence noisy third-party loggers unless verbose >= 3
    third_party_level = logging.DEBUG if verbose >= 3 else logging.WARNING
    logging.getLogger("boto3").setLevel(third_party_level)
    logging.getLogger("botocore").setLevel(third_party_level)
    logging.getLogger("urllib3").setLevel(third_party_level)
    logging.getLogger("s3transfer").setLevel(third_party_level)
