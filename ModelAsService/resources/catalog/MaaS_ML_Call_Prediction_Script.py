import json
import ast
import requests
import urllib.request
import ssl
import pandas as pd
import numpy as np

global variables

# -------------------------------------------------------------
# Get schedulerapi access and acquire session id
schedulerapi.connect()
sessionid = schedulerapi.getSession()

# -------------------------------------------------------------
# Import an external python script containing a collection of
# common utility Python functions and classes
PA_CATALOG_REST_URL = variables.get("PA_CATALOG_REST_URL")
PA_PYTHON_UTILS_URL = PA_CATALOG_REST_URL + "/buckets/machine-learning/resources/Utils_Script/raw"
req = urllib.request.Request(PA_PYTHON_UTILS_URL)
req.add_header('sessionid', sessionid)
if PA_PYTHON_UTILS_URL.startswith('https'):
    content = urllib.request.urlopen(req, context=ssl._create_unverified_context()).read()
else:
    content = urllib.request.urlopen(req).read()
exec(content, globals())

global get_input_variables, get_and_decompress_dataframe, preview_dataframe_in_task_result
global raiser_ex

def str2bool(v):
  return v.lower() in ("1", "true")

# -------------------------------------------------------------
# Get data from the propagated variables
#
SERVICE_TOKEN = variables.get("SERVICE_TOKEN") if variables.get("SERVICE_TOKEN") else variables.get(
    "SERVICE_TOKEN_PROPAGATED")
assert SERVICE_TOKEN is not None

API_PREDICT = variables.get("PREDICT_EXTENSION") if variables.get("PREDICT_EXTENSION") else raiser_ex(
    "PREDICT_EXTENSION is None")
API_ENDPOINT = variables.get("PREDICT_MODEL_ENDPOINT") if variables.get("PREDICT_MODEL_ENDPOINT") else variables.get(
    "ENDPOINT_MODEL")
assert API_ENDPOINT is not None

MODEL_NAME = variables.get("MODEL_NAME") if variables.get("MODEL_NAME") else variables.get(
    "MODEL_NAME")
assert MODEL_NAME is not None

MODEL_VERSION = int(variables.get("MODEL_VERSION")) if variables.get("MODEL_VERSION") else variables.get(
    "MODEL_VERSION")
assert MODEL_VERSION is not None

SAVE_PREDICTIONS = str2bool(variables.get("SAVE_PREDICTIONS")) if variables.get("SAVE_PREDICTIONS") else str2bool(variables.get(
    "SAVE_PREDICTIONS"))
assert SAVE_PREDICTIONS is not None

DRIFT_ENABLED = str2bool(variables.get("DRIFT_ENABLED")) if variables.get("DRIFT_ENABLED") else str2bool(variables.get(
    "DRIFT_ENABLED"))
assert DRIFT_ENABLED is not None

DRIFT_NOTIFICATION = str2bool(variables.get("DRIFT_NOTIFICATION")) if variables.get("DRIFT_NOTIFICATION") else str2bool(variables.get(
    "DRIFT_NOTIFICATION"))
assert DRIFT_NOTIFICATION is not None

API_PREDICT_ENDPOINT = API_ENDPOINT + API_PREDICT
print("API_PREDICT_ENDPOINT: ", API_PREDICT_ENDPOINT)

GET_PREDICTIONS_ENDPOINT = API_ENDPOINT + "/api/get_predictions"
print("GET_PREDICTIONS_ENDPOINT: ", GET_PREDICTIONS_ENDPOINT)

INPUT_DATA = variables.get("INPUT_DATA")
DATA_DRIFT_DETECTOR = variables.get("DATA_DRIFT_DETECTOR")

input_variables = {
    'task.dataframe_id_test': None,
    'task.dataframe_id': None,
    'task.label_column': None,
    'task.feature_names': None,
}
get_input_variables(input_variables)

is_labeled_data = False
LABEL_COLUMN = variables.get("LABEL_COLUMN")
if LABEL_COLUMN is not None and LABEL_COLUMN is not "":
    is_labeled_data = True
else:
    LABEL_COLUMN = input_variables['task.label_column']
    if LABEL_COLUMN is not None and LABEL_COLUMN is not "":
        is_labeled_data = True

dataframe_columns_name = None
if input_variables['task.dataframe_id_test'] is not None:
    dataframe_id = input_variables['task.dataframe_id_test']
    dataframe = get_and_decompress_dataframe(dataframe_id)
    if is_labeled_data:
        dataframe_test = dataframe.drop([LABEL_COLUMN], axis=1, inplace=False)
    else:
        dataframe_test = dataframe.copy()
    dataframe_columns_name = dataframe_test.columns.values
    dataframe_json = dataframe_test.to_json(orient='values')
elif input_variables['task.dataframe_id'] is not None:
    dataframe_id = input_variables['task.dataframe_id']
    dataframe = get_and_decompress_dataframe(dataframe_id)
    if is_labeled_data:
        dataframe_test = dataframe.drop([LABEL_COLUMN], axis=1, inplace=False)
    else:
        dataframe_test = dataframe.copy()
    dataframe_columns_name = dataframe_test.columns.values
    dataframe_json = dataframe_test.to_json(orient='values')
elif INPUT_DATA is not None and INPUT_DATA is not "":
    dataframe_json = variables.get("INPUT_DATA")
else:
    raiser_ex("There is no input data")

headers = {'content-type': 'application/json', 'Accept-Charset': 'UTF-8'}
data = {'predict_dataframe_json': dataframe_json, 'api_token': SERVICE_TOKEN, 'detector': DATA_DRIFT_DETECTOR, 'model_name': MODEL_NAME, 'model_version': MODEL_VERSION, 'save_predictions': SAVE_PREDICTIONS, 'drift_enabled': DRIFT_ENABLED, 'drift_notification': DRIFT_NOTIFICATION }
data_json = json.dumps(data)
req = requests.post(API_PREDICT_ENDPOINT, data=data_json, headers=headers, verify=False)

response = json.loads(req.text)
print("response ", response)
predict_and_drifts = json.loads(response)
predictions = predict_and_drifts["predictions"]
print("predictions:\n", predictions)
drifts = predict_and_drifts["drifts"]
print("drifts:\n", drifts)

PARAMS = {'api_token': SERVICE_TOKEN, 'model_name': MODEL_NAME, 'model_version': MODEL_VERSION}
req_get_predictions = requests.get(GET_PREDICTIONS_ENDPOINT, params=PARAMS, verify=False)
dataframe_json = req_get_predictions.text
dataframe = pd.read_json(dataframe_json, orient='split')
if dataframe_columns_name is not None:
    dataframe_columns_name= np.append(dataframe_columns_name,["predictions"])
    dataframe.columns = list(dataframe_columns_name)

# -------------------------------------------------------------
# Preview results
#
preview_dataframe_in_task_result(dataframe)