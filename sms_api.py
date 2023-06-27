import os
from twilio.rest import Client
from dotenv import load_dotenv
load_dotenv()

# Find your Account SID and Auth Token at twilio.com/console

class SMS():
    def __init__(self):
        account_sid = os.environ['TWILIO_ACCOUNT_SID']
        auth_token = os.environ['TWILIO_AUTH_TOKEN']
        self.client = Client(account_sid, auth_token)

    def create_msg(self, body, to, from_):
        message = self.client.messages.create(
                                      body=body,
                                      from_=from_,
                                      to=to
                )
        return message.sid
