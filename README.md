
ADSWS - ADS Web Services
========================

[![Travis Status](https://travis-ci.org/adsabs/adsws.png?branch=master)](https://travis-ci.org/adsabs/adsws)
[![Coverage Status](https://img.shields.io/coveralls/adsabs/adsws.svg)](https://coveralls.io/r/adsabs/adsws)



About
=====
Core API module for the NASA-ADS, handling:
 - authentication
 - passing requests to the correct local and/or remote microservices
 - rate limiting


Installation
============

```
    git clone https://github.com/adsabs/adsws.git
    pip install -r requirements.txt 
    alembic upgrade head
    vim instance/local_config.py # edit edit edit...
    python wsgi.py
```        

Testing
=======

```
    pip install -r dev-requirements.txt
    py.test adsws
```


Concurrency
===========

To run experiments with the concurrency and throughput:
    - use postgresql (edit adsws/config.py)
    - start the server, eg. python wsgi2.py (gevent variant)
    - run tests `ab -k -n 1000 -c 100 -H 'Authorization: Bearer:9Ffp3Ejz5d0wwnyMmgLH6oUv2vXJJYpujLm3GabY' 'http://localhost:5000/v1/test/LARGE_RATE_LIMIT/0.1'`
      - this token is anonyous, works on my machine - yours will vary

I'm certain that the DispatchMiddleware prevents gevents from running (so we are synchronous/blocking); if i use
just the api application - I can handle more requests; but it is not great