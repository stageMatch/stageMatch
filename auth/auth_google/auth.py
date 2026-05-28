import os
from authlib.integrations.flask_client import OAuth

oauth = OAuth()

def initGoogleAuth(app):
    """
    Inizializza l'oggetto OAuth per l'applicazione Flask.
    """
    oauth.init_app(app)
    oauth.register(
        name='google',
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

    return oauth.google

def getGoogleUserInfo():
    """
    Recupera le informazioni dell'utente da Google dopo l'autorizzazione.
    """
    token = oauth.google.authorize_access_token()
    user_info = token.get('userinfo')

    if user_info:
        return {
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "googleId": user_info.get("sub"),
            "picture": user_info.get("picture")
        }

    return None