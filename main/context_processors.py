import subprocess
from django.conf import settings
from .utils import generate_auth_token


def default_context(request):
    token = generate_auth_token()
    version = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], universal_newlines=True
    ).strip()
    return {"APPLE_DEVELOPER_TOKEN": token, "DEBUG": settings.DEBUG, "version": version}
