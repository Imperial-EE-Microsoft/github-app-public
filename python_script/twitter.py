import tweepy
import requests
import os
from requests_oauthlib import OAuth1

# Twitter API credentials
bearer_token = "AAAAAAAAAAAAAAAAAAAAACgttwEAAAAAM77rq6fcISNcdTtcEX7xhMeX2FY%3DJfAQvP6OY5ifyXOAtVNOWsA4wzPuef0JieiqJb5NJxQZ5xccCK"
client_key = "WWNrX1ZRR3lHaWZSN3lnNUtvTGc6MTpjaQ"
client_secret = "VvAoyeOuUXIOPamo-u0Bna-SW4eFlYK7ynARaiLt3AH9y9vAZx"
api_key = "zznTQsONJtS8ib4ePGnzNvE4B"
api_secret = "ACNM1wanIWc38iE2VIDXkBTJjDPGVNUdkXfNteIMiwDXwUfb2S"
access_token = "1790360584321466368-0HcSG6trQxJeFNdzlNfsQ1lsNa4dcn"
access_token_secret = "mI1pWzjENQD2ausThb2gIp9wHyBry6SJg8fvNhNL1GNPG"


client = tweepy.Client(
    bearer_token=bearer_token,
    consumer_key=api_key,
    consumer_secret=api_secret,
    access_token=access_token,
    access_token_secret=access_token_secret,
)

# Function to post a tweet
def post_tweet(text):
    response = client.create_tweet(text=text)
    if response.data:
        print("Tweet posted successfully!")
    else:
        print("Failed to post tweet")


def upload_media(filename):
    upload_url = "https://upload.twitter.com/1.1/media/upload.json"
    oauth = OAuth1(api_key, api_secret, access_token, access_token_secret)

    files = {"media": open(filename, "rb")}
    response = requests.post(upload_url, auth=oauth, files=files)

    if response.status_code == 200:
        media_id = response.json()["media_id_string"]
        return media_id
    else:
        print(f"Failed to upload media: {response.status_code}")
        print(response.text)
        return None


# Function to post a tweet with media using v2
def post_tweet_with_media_v2(text, media_filename):
    media_id = upload_media(media_filename)
    if media_id:
        response = client.create_tweet(text=text, media_ids=[media_id])
        if response.data:
            print("Tweet with media posted successfully!")
        else:
            print("Failed to post tweet with media")
    else:
        print("Failed to upload media, tweet not posted")


post_tweet_with_media_v2(
    "Hello Twitter with media!",
    "C:/Users/27846/Desktop/Projects/github-app/python_script/cat.jpg",
)
