import os
import logging
from hashlib import sha1
from apishiv import app

logging.basicConfig(level=logging.DEBUG)
app.secret_key = 'b63a3eb385a757d41ff5217f96d1bef965a6f657'

if __name__ == '__main__':
    app.run('0.0.0.0', 3333, debug=True)
