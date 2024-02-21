from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
#from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from msrest.authentication import CognitiveServicesCredentials

from array import array
import os
from PIL import Image
import sys
import time

# Import endpoints and api key
from env import cv_endpoint, cv_api_key

start_time = time.time()

# Setup CV prediction client
computervision_client = ComputerVisionClient(cv_endpoint, CognitiveServicesCredentials(cv_api_key))

#local_image_path = "HISTOPATHOLOGY-COLONOSCOPY-WITH-POLYPECTOMY-BIOPSY-report-format-example-sample-template-Drlogy-lab-report.tiff"
local_image_path = "megadoc.tif"
pdf_path = "https://images.drlogy.com/assets/uploads/lab/pdf/HISTOPATHOLOGY-COLONOSCOPY-WITH-POLYPECTOMY-BIOPSY-report-format-example-sample-template-Drlogy-lab-report.pdf"

url = False

if url == True:
    read_response = computervision_client.read(pdf_path, raw=True)
else:
    with open(local_image_path, "rb") as image_stream:
        read_response = computervision_client.read_in_stream(image_stream, raw=True)
            
# Get the operation location (URL with an ID at the end) from the response
read_operation_location = read_response.headers["Operation-Location"]
# Grab the ID from the URLW
operation_id = read_operation_location.split("/")[-1]

# Call the "GET" API and wait for it to retrieve the results 
while True:
    read_result = computervision_client.get_read_result(operation_id)
    if read_result.status not in ['notStarted', 'running']:
        break
    time.sleep(1)

# Print the detected text, line by line
if read_result.status == OperationStatusCodes.succeeded:
    for text_result in read_result.analyze_result.read_results:
        for line in text_result.lines:
            print(line.text)
            #print(line.bounding_box)

# Calculate script run time and print    
end_time = time.time()
total_time = end_time - start_time
print(f"Total script run time: {total_time} seconds")
