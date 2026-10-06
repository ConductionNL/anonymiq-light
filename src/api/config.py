import logging.config
import os

from dotenv import load_dotenv

load_dotenv()


def parse_allowed_origins(raw: str | None) -> list[str]:
    """Parse a comma separated ALLOWED_ORIGINS value into a list of origins.

    Unset or empty gives an empty list, which leaves CORS off. A trailing slash
    is dropped, because a browser sends the origin without one.

    Args:
        raw: The raw environment value, or None when it is not set.

    Returns:
        list[str]: The explicit origins, in the order given.
    """
    if not raw:
        return []
    return [part.strip().rstrip("/") for part in raw.split(",") if part.strip()]


class Settings:
    """Applicatieconfiguratie voor de Presidio-NL API.

    Bevat standaardwaarden voor debugmodus, ondersteunde entiteiten, taal,
    en de te gebruiken NLP-modellen (spaCy).
    """

    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    # Default entity types returned when no filter is specified.
    # Covers the most common PII — all recognizers may produce additional types.
    DEFAULT_ENTITIES = [
        "PERSON",
        "LOCATION",
        "ORGANIZATION",
        "PHONE_NUMBER",
        "EMAIL",
        "IBAN",
        "BSN",
        "DATE",
    ]

    # Full set of entity types produced by all registered recognizers.
    # Used for request validation and Swagger documentation.
    ALL_SUPPORTED_ENTITIES = [
        # NER (SpaCy/GLiNER)
        "PERSON",
        "LOCATION",
        "ORGANIZATION",
        "NORP",
        # Pattern recognizers
        "PHONE_NUMBER",
        "EMAIL",
        "IBAN",
        "BSN",
        "DATE",
        "ID_NO",
        "DRIVERS_LICENSE",
        "CASE_NO",
        "VAT_NUMBER",
        "KVK_NUMBER",
        "LICENSE_PLATE",
        "IP_ADDRESS",
        "POSTCODE",
        "MAC_ADDRESS",
        "SOCIAL_MEDIA",
        "TIME",
        "CREDIT_CARD",
    ]

    DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "nl")
    DEFAULT_SPACY_MODEL = os.getenv("DEFAULT_SPACY_MODEL", "nl_core_news_lg")

    # CORS is off unless a deployment names its browser origins (comma
    # separated). The known callers, OpenRegister directly or through the
    # AppAPI proxy, are server to server and send no Origin header, so they
    # need no CORS at all.
    ALLOWED_ORIGINS: list[str] = parse_allowed_origins(os.getenv("ALLOWED_ORIGINS"))


settings: Settings = Settings()


def setup_logging() -> None:
    """Configureer logging voor de applicatie.

    Stelt zowel een file- als streamhandler in, met DEBUG- of INFO-niveau
    afhankelijk van de configuratie. Logt naar 'app.log' en de console.
    """
    console_log_level = "DEBUG" if settings.DEBUG else "INFO"
    log_dir = os.getenv("LOG_DIR", "/tmp/logs")
    os.makedirs(log_dir, exist_ok=True)
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "file": {
                    "class": "logging.FileHandler",
                    "formatter": "default",
                    "level": "DEBUG",
                    "filename": os.path.join(log_dir, "app.log"),
                },
                "stream": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": console_log_level,
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": "DEBUG",
                "handlers": ["file", "stream"],
            },
        }
    )

    logging.debug("Logging is configured.")
