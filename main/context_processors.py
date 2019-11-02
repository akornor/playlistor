from .utils import generate_auth_token


def default_context(request):
    token = generate_auth_token()
    return {"APPLE_DEVELOPER_TOKEN": token}
