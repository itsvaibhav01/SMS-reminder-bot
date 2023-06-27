import os
from flask import Flask, request, Response, render_template
from chatbot import ChatBot
from dotenv import load_dotenv
load_dotenv()

import logging

app = Flask(__name__)
bot = ChatBot(os.environ['PHONE_NUMBER'])
# logging
logging.basicConfig(level=logging.INFO)

@app.route('/', methods=['GET'])
def index():
    app.logger.info('log: get')
    return render_template('index.html')

# Webhook endpoint for receiving incoming SMS
@app.route('/sms', methods=['POST'])
def handle_sms():
    app.logger.info('log: post sms')

    # Convert the form data to json
    form_dict = dict(request.form)
    
    # Create the ChatBot object
    app.logger.info('form data: %s', str(form_dict))

    return bot.Processingـincomingـmessages(form_dict)

# Start the server
if __name__ == '__main__':
    app.run(debug=True)
