import hashlib
import hmac
import boto3
import os
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from typing import Any
import json
import urllib.parse
import re

slack_signing_secret = bytes(os.environ["SLACK_SIGNING_SECRET"], "utf-8")
api_key = os.environ["I90_API_KEY"]

retry_strategy = Retry(
    total=3,
    status_forcelist=[429, 500, 502, 503, 504],
    method_whitelist=["HEAD", "GET", "OPTIONS", "PUT"],
    backoff_factor=1,
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", adapter)

# From django: https://github.com/django/django/blob/stable/1.3.x/django/core/validators.py#L45
url_re = re.compile(
    r"^(?:http|ftp)s?://"  # http:// or https://
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
    r"localhost|"  # localhost...
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
    r"(?::\d+)?"  # optional port
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)

token_re = re.compile("^[a-zA-Z0-9_-]+$")

HELP_TEXT = """
You can type `/shorten https://example.com` to shorten a URL with a random name (e.g. `https://go.voteamerica.com/umd8sj3f`),
or you can type `/shorten https://example.com as some-name` to shorten a URL to a specific name (e.g. `https://go.voteamerica.com/some-name`).
"""


def verify_slack_request(event: Any):
    """
    From: https://janikarhunen.fi/verify-slack-requests-in-aws-lambda-and-python
    """
    slack_signature = event["headers"]["X-Slack-Signature"]
    slack_request_timestamp = event["headers"]["X-Slack-Request-Timestamp"]

    request_body = event["body"]

    basestring = f"v0:{slack_request_timestamp}:{request_body}".encode("utf-8")

    my_signature = (
        "v0=" + hmac.new(slack_signing_secret, basestring, hashlib.sha256).hexdigest()
    )

    if not hmac.compare_digest(my_signature, slack_signature):
        print(
            f"Verification failed.\nmy_signature: {my_signature}\nslack_signature: {slack_signature}"
        )

        raise RuntimeError("Invalid Slack signature")


def handler(event: Any, context: Any):
    verify_slack_request(event)

    params = {k: v for k, v in urllib.parse.parse_qsl(event["body"])}

    # Slack's formatting crap sometimes uses non-breaking spaces around URLs,
    # so we translate those to normal spaces
    command = params["text"].replace("\xa0", " ")
    command_parts = command.split(" ")

    if command.strip().lower() == "help":
        reply = HELP_TEXT

    if len(command_parts) == 1 and command_parts[0].strip().lower() != "help":
        # just the URL
        url = command_parts[0]
        if not url_re.match(url):
            reply = "Sorry, that's not a valid URL.\n\n" + HELP_TEXT
        else:
            resp = http.post(
                "https://go.voteamerica.com/v1/conceive",
                headers={"x-api-key": api_key,},
                json={
                    "destination": url,
                    "_app_name": "slack",
                    "_slack_user_name": params["user_name"],
                },
            )

            if 400 <= resp.status_code < 500:
                reply = f"Uh oh, I couldn't create that link for you: {resp.json()['error']}"
            else:
                resp.raise_for_status()
                reply = f"Success! {resp.json()['short_url']} now goes to {url}"

    elif len(command_parts) == 3 and command_parts[1].lower() == "as":
        # URL and token
        url, _, token = command_parts
        if not url_re.match(url):
            reply = "Sorry, that's not a valid URL.\n\n" + HELP_TEXT
        elif not token_re.match(token):
            reply = (
                "Sorry, short URL names can only contain letters, numbers, `_`, and `-`.\n\n"
                + HELP_TEXT
            )
        else:
            resp = http.post(
                "https://go.voteamerica.com/v1/claim",
                headers={"x-api-key": api_key,},
                json={
                    "token": token,
                    "destination": url,
                    "_app_name": "slack",
                    "_slack_user_name": params["user_name"],
                },
            )

            if 400 <= resp.status_code < 500:
                reply = f"Uh oh, I couldn't create that link for you: {resp.json()['error']}"
            else:
                resp.raise_for_status()
                reply = f"Success! {resp.json()['short_url']} now goes to {url}"
    else:
        # Print usage
        print(command_parts)
        reply = "Sorry, I don't understand that.\n\n" + HELP_TEXT

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"response_type": "in_channel", "text": reply}),
    }
