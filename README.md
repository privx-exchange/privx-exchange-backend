# privx-xyz-backend
This repo works as Privx.xyz backend service, do below tasks:
1. Sync with aleo chain to retrieve orders.
2. Trade with orders and notify new-generated trades onchain.
3. Provide rest api for privx-xyz-frontend.
## Prepare env file
```
$ cat .env
NODE_HOST=http://127.0.0.1:3030
CONTRACT_HOST=http://127.0.0.1:4040
PSQLURL=postgresql://xxx:xxxxxx@127.0.0.1:5436/root
PRIVATE_KEY=APrivateKeyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```
## Deploy Guide
```bash
$ pip install -r requirements.txt
$ python init_db.py
$ python main.py
```