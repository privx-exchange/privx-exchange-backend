# privx-exchange-backend
This repo works as Privx.exchange backend service, do below tasks:
1. Sync with aleo chain to retrieve orders.
2. Trade with orders and notify new-generated trades onchain.
3. Provide rest api for privx-exchange-frontend.
## Prepare env file
```
$ cat .env
NODE_HOST=http://127.0.0.1:3030
CONTRACT_HOST=http://127.0.0.1:4040
PSQLURL=postgresql://xxx:xxxxxx@127.0.0.1:5436/root
PRIVATE_KEY=APrivateKeyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
CONTRACT_NAME=privx_exchange.aleo
```
## Deploy Guide
```bash
$ pip install -r requirements.txt
$ python init_db.py
$ python main.py
```