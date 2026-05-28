import os
from pathlib import Path


def get_secret(secret_name, env_var=None, default=""):
    """
    Read a secret from Docker secrets (file at /run/secrets/<name>),
    falling back to an environment variable for dev/non-Docker environments.
    """
    secret_path = Path(f"/run/secrets/{secret_name}")
    if secret_path.is_file():
        return secret_path.read_text().strip()
    var = env_var or secret_name.upper()
    return os.environ.get(var, default)
