import os

class Config:
    SECRET_KEY = os.urandom(24) 
    SESSION_PERMANENT = True
    SESSION_TYPE = "filesystem"