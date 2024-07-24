import xendit
import os
from xendit.apis import PaymentRequestApi
from xendit.payment_request.model.payment_request_parameters import PaymentRequestParameters
from xendit.payment_request.model.error import Error
from xendit.payment_request.model.payment_request import PaymentRequest
from pprint import pprint
from dotenv import load_dotenv

load_dotenv()

xendit.set_api_key(os.environ.get("XENDIT_API_KEY"))

# Enter a context with an instance of the API client
api_client = xendit.ApiClient()
# Create an instance of the API class
api_instance = PaymentRequestApi(api_client)
# idempotency_key = "5f9a3fbd571a1c4068aa40ce" # str 
# for_user_id = "5f9a3fbd571a1c4068aa40cf" # str 
payment_request_parameters = {
  "reference_id" : "example-ref-1234",
  "currency" : "IDR",
  "amount" : 15000,
  "country" : "ID",
  "payment_method" : {
    "type" : "VIRTUAL_ACCOUNT",
    "reusability" : "ONE_TIME_USE",
    "reference_id" : "example-1234",
    "virtual_account" : {
      "channel_code" : "BNI",
      "channel_properties" : {
        "customer_name" : "Ahmad Gunawan",
        "expires_at" : "2024-08-03T17:00:00Z"
      }
    }
  }
} # PaymentRequestParameters 

# example passing only required values which don't have defaults set
# and optional values
try:
    # Create Payment Request
    api_response = api_instance.create_payment_request(payment_request_parameters=payment_request_parameters)
    pprint(api_response)
except xendit.XenditSdkException as e:
    print("Exception when calling PaymentRequestApi->create_payment_request: %s\n" % e)