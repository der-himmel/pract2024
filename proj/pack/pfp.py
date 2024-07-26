import os
import requests

from .database import PROFILE_PICTURES_PATH

def generate_pfp(username):
    pfp_path = os.path.join(PROFILE_PICTURES_PATH, username) + ".jpg"
    with open(pfp_path,'wb') as profile_photo:
        profile_photo.write(requests.get(
            'https://thispersondoesnotexist.com',
            headers={'User-Agent': 'My User Agent 1.0'},
            verify=True
        ).content)
        profile_photo.close()

def save_pfp(username, pfp):
    pfp_path = os.path.join(PROFILE_PICTURES_PATH, username) + '.jpg'
    # pfp_path = os.path.join(PROFILE_PICTURES_PATH, username)
    with open(pfp_path, "wb") as profile_photo:
        profile_photo.write(pfp.file.read())
        profile_photo.close()
