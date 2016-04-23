import os
import random
import string

import time
from flask import Flask, render_template, request
from celery import Celery
import requests

JOBCOIN_BASE_API = 'http://jobcoin.projecticeland.net/anopsia/api/'

app = Flask(__name__)
app.config['CELERY_BROKER_URL'] = os.environ['REDIS_URL']
app.config['CELERY_RESULT_BACKEND'] = os.environ['REDIS_URL']
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


def address_is_valid(address):
    url = JOBCOIN_BASE_API + 'addresses/' + address
    response = requests.get(url)
    json_response = response.json()
    balance = float(json_response['balance'])
    number_of_transactions = len(json_response['transactions'])
    if (balance != 0) or (number_of_transactions != 0):
        return False
    else:
        return True


def addresses_are_valid(addresses):
    for address in addresses:
        if not address_is_valid(address):
            return False
    return True


@celery.task
def start_background_mixing_task(addresses, deposit_address):
    while address_is_valid(deposit_address):
        time.sleep(20)
    print 'JobCoins deposited.'


def generate_deposit_address():
    symbols = string.ascii_uppercase + string.ascii_lowercase + string.digits
    generated_address = ''.join(random.SystemRandom().choice(symbols) for _ in range(16))
    while not address_is_valid(generated_address):
        generated_address = ''.join(random.SystemRandom().choice(symbols) for _ in range(16))
    return generated_address


@app.route('/', methods=['GET', 'POST'])
def index():
    error = None
    if request.method == 'POST':
        if request.form['addresses']:
            addresses = request.form['addresses'].split()
            if addresses_are_valid(addresses):
                deposit_address = generate_deposit_address()
                start_background_mixing_task(addresses, deposit_address)
                return render_template('deposit.html', deposit_address=deposit_address)
            else:
                error = 'At least one of the supplied addresses was not new and unused.'
        else:
            error = 'No addresses were supplied.'
    return render_template('index.html', error=error)

if __name__ == '__main__':
    app.debug = True
    app.run()
