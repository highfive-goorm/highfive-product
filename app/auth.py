from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

SECRET_KEY = os.environ['secret_key']

ALGORITHM = "HS256"


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        account = payload.get("account")
        if account is None:
            raise HTTPException(status_code=400, detail="Invalid JWT")
        return {"account": account}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
