import os

class Config:
    SECRET_KEY = os.urandom(24)  # Change this to a fixed secret key
    SESSION_PERMANENT = True
    SESSION_TYPE = "filesystem"