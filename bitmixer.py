import os
import random
import string

import time
from flask import Flask, render_template, request
from celery import Celery
import requests

JOBCOIN_BASE_API = 'http://jobcoin.projecticeland.net/anopsia/api/'
RESERVE_CHAIN_ADDRESS = 'BitMixerReserveChain'

app = Flask(__name__)
app.config['CELERY_BROKER_URL'] = os.environ['REDIS_URL']
app.config['CELERY_RESULT_BACKEND'] = os.environ['REDIS_URL']
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


def address_is_valid(address):
    url = JOBCOIN_BASE_API + 'addresses/' + address
    json_response = get_address_info(url)
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


def get_address_info(url):
    response = requests.get(url)
    json_response = response.json()
    return json_response


def make_transaction(from_address, to_address, amount):
    transaction_url = JOBCOIN_BASE_API + 'transactions'
    post_data = {
        'fromAddress': from_address,
        'toAddress': to_address,
        'amount': str(amount)
    }
    requests.post(transaction_url, data=post_data)


def mix(addresses, balance):
    print balance
    for address in addresses[:-1]:
        amount = 0
        if balance > 0:
            amount = balance - random.SystemRandom().uniform(0, balance)
            balance = balance - amount
        print balance
        make_transaction(RESERVE_CHAIN_ADDRESS, address, amount)
    make_transaction(RESERVE_CHAIN_ADDRESS, addresses[-1], balance)
    print balance


@celery.task(name='bitmixer.mix_in_background')
def mix_in_background(addresses, deposit_address):
    while address_is_valid(deposit_address):
        time.sleep(20)
    url = JOBCOIN_BASE_API + 'addresses/' + deposit_address
    json_response = get_address_info(url)
    balance = float(json_response['balance'])
    make_transaction(deposit_address, RESERVE_CHAIN_ADDRESS, balance)
    mix(addresses, balance)


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
                mix_in_background.apply_async((addresses, deposit_address))
                return render_template('deposit.html', deposit_address=deposit_address)
            else:
                error = 'At least one of the supplied addresses was not new and unused.'
        else:
            error = 'No addresses were supplied.'
    return render_template('index.html', error=error)

if __name__ == '__main__':
    app.debug = True
    app.run()
