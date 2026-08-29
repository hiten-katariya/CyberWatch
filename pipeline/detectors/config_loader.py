import os
import yaml
import logging

logger = logging.getLogger("config-loader")

def load_detector_config(config_path="config/detectors.yaml"):
    possible_paths = [
        config_path,
        os.path.join(os.path.dirname(__file__), "../../config/detectors.yaml"),
        "/app/config/detectors.yaml"
    ]
    for p in possible_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    conf = yaml.safe_load(f)
                    logger.info(f"Loaded detector configuration from {p}")
                    return conf
            except Exception as e:
                logger.error(f"Error reading config file {p}: {e}")
    logger.warning("Config file detectors.yaml not found. Using default fallback configuration.")
    return {}
