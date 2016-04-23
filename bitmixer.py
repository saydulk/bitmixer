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


@app.route('/', methods=['GET', 'POST'])
def index():
    """Handle the apps requests"""
    error = None
    if request.method == 'POST':
        # Perform data validation on supplied addresses.
        if request.form['addresses']:
            addresses = request.form['addresses'].split()
            if addresses_are_valid(addresses):
                deposit_address = generate_valid_address()
                # Give the user 1 hour to deposit the JobCoins
                mix_in_background.apply_async((addresses, deposit_address), expires=3600)
                return render_template('deposit.html', deposit_address=deposit_address)
            else:
                error = 'At least one of the supplied addresses was not new and unused.'
        else:
            error = 'No addresses were supplied.'
    return render_template('index.html', error=error)


def addresses_are_valid(addresses):
    """Check the list of addresses supplied are new and unused"""
    for address in addresses:
        if not address_is_valid(address):
            return False
    return True


def address_is_valid(address):
    """Check the supplied address is new and unused"""
    url = JOBCOIN_BASE_API + 'addresses/' + address
    json_response = get_address_info(url)
    balance = float(json_response['balance'])
    number_of_transactions = len(json_response['transactions'])
    if (balance != 0) or (number_of_transactions != 0):
        return False
    else:
        return True


def get_address_info(url):
    """Return info for the supplied URL"""
    response = requests.get(url)
    json_response = response.json()
    return json_response


def generate_valid_address():
    """Return a valid (new and unused) 16 char JobCoin address"""
    symbols = string.ascii_uppercase + string.ascii_lowercase + string.digits
    generated_address = ''.join(random.SystemRandom().choice(symbols) for _ in range(16))
    while not address_is_valid(generated_address):
        generated_address = ''.join(random.SystemRandom().choice(symbols) for _ in range(16))
    return generated_address


def get_current_balance(address):
    """Return the current balance of the supplied address"""
    url = JOBCOIN_BASE_API + 'addresses/' + address
    json_response = get_address_info(url)
    return float(json_response['balance'])


@celery.task(name='bitmixer.mix_in_background')
def mix_in_background(addresses, deposit_address):
    """In the background, poll the deposit address until JobCoins deposited, then mix them back into the addresses"""
    # Check if transaction has been made every 20 seconds
    while address_is_valid(deposit_address):
        time.sleep(20)
    # Get the amount of JobCoins to mix
    amount = get_current_balance(deposit_address)
    # Move the JobCoins from the deposit address to the BitMixerReserveChain
    make_transaction(deposit_address, RESERVE_CHAIN_ADDRESS, amount)
    # Mix that amount back in to the initially supplied addresses
    mix(addresses, amount)


def make_transaction(from_address, to_address, amount):
    """Transfer JobCoins from one address to another"""
    transaction_url = JOBCOIN_BASE_API + 'transactions'
    post_data = {
        'fromAddress': from_address,
        'toAddress': to_address,
        'amount': str(amount)
    }
    requests.post(transaction_url, data=post_data)


def mix(addresses, total_amount):
    """Mix the amount provided into the supplied addresses"""
    for address in addresses[:-1]:
        transfer_amount = 0
        if total_amount > 0:
            # Transfer a random amount of the funds to all but the last address
            transfer_amount = round((total_amount - random.SystemRandom().uniform(0, total_amount)), 6)
            total_amount -= transfer_amount
        make_transaction(RESERVE_CHAIN_ADDRESS, address, transfer_amount)
    # Transfer the remaining total amount to the last address
    make_transaction(RESERVE_CHAIN_ADDRESS, addresses[-1], total_amount)


if __name__ == '__main__':
    app.run()
