import logging


def configure_logging(debug: bool) -> None:
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
