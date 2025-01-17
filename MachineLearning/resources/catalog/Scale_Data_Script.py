
# -*- coding: utf-8 -*-
"""Proactive Scale Data for Machine Learning

This module contains the Python script for the Scale Data task.
"""
import ssl
import urllib.request

global variables, resultMetadata

__file__ = variables.get("PA_TASK_NAME")
print("BEGIN " + __file__)

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
global check_task_is_enabled, preview_dataframe_in_task_result
global get_and_decompress_dataframe, compress_and_transfer_dataframe
global assert_not_none_not_empty, get_input_variables, scale_columns

# -------------------------------------------------------------
# Check if the Python task is enabled or not
check_task_is_enabled()

# -------------------------------------------------------------
# Get data from the propagated variables
#
COLUMNS_NAME = variables.get("COLUMNS_NAME")
SCALER_NAME = variables.get("SCALER_NAME")

assert_not_none_not_empty(COLUMNS_NAME, "COLUMNS_NAME should be defined!")
assert_not_none_not_empty(SCALER_NAME, "SCALER_NAME should be defined!")

input_variables = {
    'task.dataframe_id': None,
    'task.label_column': None
}
get_input_variables(input_variables)

dataframe_id = input_variables['task.dataframe_id']
print("dataframe id (in): ", dataframe_id)

dataframe = get_and_decompress_dataframe(dataframe_id)

# Apply a given Scaler to the DataFrame
columns = [x.strip() for x in COLUMNS_NAME.split(',')]
dataframe, scaler = scale_columns(dataframe, columns, SCALER_NAME)

# -------------------------------------------------------------
# Transfer data to the next tasks
#
dataframe_id = compress_and_transfer_dataframe(dataframe)
print("dataframe id (out): ", dataframe_id)

resultMetadata.put("task.name", __file__)
resultMetadata.put("task.dataframe_id", dataframe_id)
resultMetadata.put("task.label_column", input_variables['task.label_column'])

# -------------------------------------------------------------
# Preview results
#
preview_dataframe_in_task_result(dataframe)

# -------------------------------------------------------------
print("END " + __file__)