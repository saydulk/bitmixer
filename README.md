# bitmixer

[JobCoin](http://jobcoin.projecticeland.net/anopsia) toy [bitmixer](https://bitmixer.io/how.html). Live version hosted [here](https://bitmixer.herokuapp.com/).

## to run locally
Requirements: redis, python2.7, virtualenv
```
git clone https://github.com/JmsBtlr111/bitmixer.git
cd bitmixer
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
export REDIS_URL=redis://localhost:6379
```
In another terminal, run redis:
```
redis-server
```
In the original terminal, start the app and [celery](http://www.celeryproject.org/) in the background:
```
gunicorn bitmixer:app --log-file - &; celery worker --app=bitmixer.celery &
```
You should be able to visit `localhost:8000` in your own browser now.
