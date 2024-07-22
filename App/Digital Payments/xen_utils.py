import xendit, os
from xendit.apis import BalanceApi
from pprint import pprint
from dotenv import load_dotenv

# load_dotenv()

xendit.set_api_key(os.environ.get("XENDIT_API_KEY"))

client = xendit.ApiClient()

try:
    response = BalanceApi(client).get_balance('CASH')
    pprint(response)
except xendit.XenditSdkException as e:
    print("Exception when calling BalanceApi->get_balance: %s\n" % e)