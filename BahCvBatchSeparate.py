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
from env import cv_endpoint, cv_api_key, cv_endpoint2, cv_api_key2

# Setup CV prediction client
computervision_client = ComputerVisionClient(cv_endpoint, CognitiveServicesCredentials(cv_api_key))
computervision_client2 = ComputerVisionClient(cv_endpoint2, CognitiveServicesCredentials(cv_api_key2))

# Setup paths
tiff_path = "megadoc.tif"  # Change this to the path of your TIFF file
output_dir = "output"  # Change this to your desired output directory

# Set parameters - This is where you can tune performance, etc.
quality = 80
dpi = 200
max_width_inches = 8.5
max_width_pixels = int(max_width_inches * dpi)
sleep_time = 0.01
intermediate = "file"
greyscale = True

# Set max number of threads to create
max_workers = 10
max_workers_ocr = 40

start_time = time.time()

def process_page(i, frame):
    print(f"Processing page {i}...")
    
    if greyscale == True and frame.mode != "L":
        print(f"Converting {i} from {frame.mode} to Greyscale...")
        frame = frame.convert("L")
    # Check for alpha channels and if found, remove them:
    elif frame.mode == "RGBA":
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
        ig = open(jpg_path, "rb")
    else:
        ig = io.BytesIO()
        frame.save(ig, "JPEG", quality=80, dpi=(dpi, dpi))
        ig.seek(0)

    print(f"Finished transforming image {i}...")
#    return (i, ig, len(ig.getvalue()))
    return (i, ig)

def ocr_page(i, ig):
#def ocr_page(i, ig, sz):
    ocr_start_time = time.time()
    print(f"Starting OCR of image {i}...")
    if i % 2 == 0: 
        cv = computervision_client
    else:
        cv = computervision_client2

    read_response = cv.read_in_stream(ig, raw=True)

    # Get the operation location (URL with an ID at the end) from the response
    read_operation_location = read_response.headers["Operation-Location"]

    # Grab the ID from the URLW
    operation_id = read_operation_location.split("/")[-1]
    
    # Call the API and wait for it to provide the results 
    while True:
        read_result = cv.get_read_result(operation_id)
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

    ocr_end_time = time.time()
    ocr_total_time = ocr_end_time - ocr_start_time

    # Return the page number and OCR text
#    return ([i, sz, ocr_text, ocr_total_time])
    return ([i, ocr_text, ocr_total_time])

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

    # Collate the results of the image conversion processing
    print("Collating results of image transformation...")
    results = []
    for f in futures:
        results.append(f.result())
    df_images = pd.DataFrame(results,columns=['Page','Image'])
#    df_images = pd.DataFrame(results,columns=['Page','Image','Size'])
    #df_images = df_images.sort_values(by='Size',ascending=True)    

    # Calculate script run time and print final run time
    end_time = time.time()
    total_time = end_time - start_time
    print(f"Total run time for image transformation: {total_time:.1f} seconds")

    # Multithread process the OCR of the transformed images
    with Image.open(tiff_path) as img:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers_ocr) as executor:
            #futures_ocr = [executor.submit(ocr_page, i, ig) for i, ig in results]
            futures_ocr = [executor.submit(ocr_page, row['Page'], row['Image']) for index, row in df_images.iterrows()]
#            futures_ocr = [executor.submit(ocr_page, row['Page'], row['Image'], row['Size']) for index, row in df_images.iterrows()]
    
            for future in concurrent.futures.as_completed(futures_ocr):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error: {e}")

    # Collate the results of the OCR processing
    print("Collating results of OCR processing...")
    results_ocr = []
    for f in futures_ocr:
        results_ocr.append(f.result())
 #   df_results = pd.DataFrame(results_ocr,columns=['Page','Size','Text','OCR time'])
    df_results = pd.DataFrame(results_ocr,columns=['Page','Text','OCR time'])

    # Save the results to CSV
    df_results.to_csv("results.csv",index=False)
    print("Processing completed and results saved.")

    # Calculate script run time and print final run time
    end_time = time.time()
    total_time = end_time - start_time
    print(f"Total script run time: {total_time:.1f} seconds")

if __name__ == "__main__":
    main()    
