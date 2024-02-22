from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import json, requests, time
from PIL import Image, ImageSequence
import os, io
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
#from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from msrest.authentication import CognitiveServicesCredentials
import concurrent.futures
import pandas as pd

# Import endpoints and api key
from env import cv_endpoint, cv_api_key

# Setup CV prediction client
computervision_client = ComputerVisionClient(cv_endpoint, CognitiveServicesCredentials(cv_api_key))

# Setup paths
tiff_path = "megadoc.tif"  # Change this to the path of your TIFF file
output_dir = "output"  # Change this to your desired output directory

# Set parameters - This is where you can tune performance, etc.
quality = 80
dpi = 200
max_width_inches = 8.5
max_width_pixels = int(max_width_inches * dpi)
sleep_time = 0.01
intermediate = "bytesio"

# Set max number of threads to create
max_workers = 30

start_time = time.time()

def process_page(i, frame):
    print(f"Processing page {i}...")
    
    # Check for alpha channels and if found, remove them:
    if frame.mode == "RGBA":
        print(f"Converting {i} to RGB from RGBA...")
        frame = frame.convert("RGB")
    elif frame.mode == "LA":
        print(f"Converting {i} to L from LA...")
        frame = frame.convert("L")
    
    # Check image size and scale down if too large, maintaining aspect ratio
    original_width, original_height = frame.size
    if original_width > max_width_pixels:
        print(f"Resizing image {i}...")
        # Calculate the new height to maintain aspect ratio
        new_height = int((max_width_pixels / original_width) * original_height)
        frame = frame.resize((max_width_pixels, new_height))

        # Set the DPI
        frame.info['dpi'] = (dpi, dpi)

    if intermediate == "file":
        # Create a filename for the resulting JPEG
        jpg_path = os.path.join(output_dir, f"frame_{i}.jpg")

        # Save the current frame as a JPEG
        frame.save(jpg_path, "JPEG", quality=80, dpi=(dpi, dpi))
    else:
        ig = io.BytesIO()
        frame.save(ig, "JPEG", quality=80, dpi=(dpi, dpi))
        ig.seek(0)

    print(f"Finished transforming image {i}...")

    if intermediate == "file":
        # Open the saved JPEG and send to CV API to process
        with open(jpg_path, "rb") as image_stream:
            read_response = computervision_client.read_in_stream(image_stream, raw=True)
    else:
        # Use ioBytes object to call CV API to process
        with ig as image_stream:
            read_response = computervision_client.read_in_stream(image_stream, raw=True)

    # Get the operation location (URL with an ID at the end) from the response
    read_operation_location = read_response.headers["Operation-Location"]

    # Grab the ID from the URLW
    operation_id = read_operation_location.split("/")[-1]
    
    # Call the API and wait for it to provide the results 
    while True:
        read_result = computervision_client.get_read_result(operation_id)
        if read_result.status not in ['notStarted', 'running']:
            break
        # Sleep until calling the API again
        time.sleep(sleep_time)
    
    # Capture the detected text, line by line
    ocr_text = ""
    if read_result.status == OperationStatusCodes.succeeded:
        for text_result in read_result.analyze_result.read_results:
            for line in text_result.lines:
                ocr_text = ocr_text + line.text
    print(f"Finished OCR of image {i}...")

    # Return the page number and OCR text
    return ([i, ocr_text])

def main():
    
    print(f"This machine has {os.cpu_count()} CPU cores")
    start_time = time.time()

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Multithread process the TIFF into JPEG and adjust them
    with Image.open(tiff_path) as img:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_page, i, f.copy()) for i, f in enumerate(ImageSequence.Iterator(img))]
    
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error: {e}")

    # Collate the results of the OCR processing
    print("Collating results...")
    results = []
    for f in futures:
        results.append(f.result())
    df_results = pd.DataFrame(results,columns=['Page','Text'])

    # Save the results to CSV
    df_results.to_csv("results.csv",index=False)
    print("Processing completed and results saved.")

    # Calculate script run time and print final run time
    end_time = time.time()
    total_time = end_time - start_time
    print(f"Total script run time: {total_time:.1f} seconds")

if __name__ == "__main__":
    main()    
