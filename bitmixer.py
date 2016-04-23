from flask import Flask, render_template, request
from celery import Celery
import requests

JOBCOIN_BASE_API = 'http://jobcoin.projecticeland.net/anopsia/api/'

app = Flask(__name__)


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


@app.route('/', methods=['GET', 'POST'])
def index():
    error = None
    if request.method == 'POST':
        if request.form['addresses']:
            addresses = request.form['addresses'].split()
            if addresses_are_valid(addresses):
                #redirect
                pass
            else:
                error = 'At least one of the supplied addresses was not new and unused.'
        else:
            error = 'No addresses were supplied.'
    return render_template('index.html', error=error)

if __name__ == '__main__':
    app.debug = True
    app.run()
