import os


class Config:
    # APP SECRET KEY
    SECRET_KEY = os.environ.get("SECRET_KEY")
    # OMI_CONFIG
    OMI_APP_ID = os.environ.get("OMI_APP_ID")
    OMI_API_KEY = os.environ.get("OMI_API_KEY")
    OMI_API_URL = os.environ.get("OMI_API_URL", "https://api.omi.me/v2")
    # SLACK_CONFIG
    BOT_SCOPE = "chat:write,files:read"
    SLACK_CLIENT_ID = os.environ.get("SLACK_CLIENT_ID")
    SLACK_AUTH_URL = "https://slack.com/oauth/v2/authorize"
    SLACK_TOKEN_URL = "https://slack.com/api/oauth.v2.access"
    SLACK_REDIRECT_URI = os.environ.get("SLACK_REDIRECT_URI")
    SLACK_CLIENT_SECRET = os.environ.get("SLACK_CLIENT_SECRET")
    SLACK_SCOPE = "channels:read,groups:read,im:read,mpim:read,users:read,chat:write,channels:history,groups:history,mpim:history,im:history,files:read"
