from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import json, requests, time

# Import endpoints and api key
from env import azure_endpoint, api_key

start_time = time.time()

# Path to PDF file
#pdf_path = "sample2_medical_report.pdf"
pdf_path = "https://images.drlogy.com/assets/uploads/lab/pdf/HISTOPATHOLOGY-COLONOSCOPY-WITH-POLYPECTOMY-BIOPSY-report-format-example-sample-template-Drlogy-lab-report.pdf"

model_type = "prebuilt-document"
#model_type = "prebuilt-read"

# Create Doc Intelligence Client
client = DocumentAnalysisClient(azure_endpoint, AzureKeyCredential(api_key))

# Read the PDF file
if pdf_path[0:6]=="https:":
    pdf_bytes = requests.get(pdf_path)
else:
    with open(pdf_path, "rb") as pdf_file:
       pdf_bytes = pdf_file.read()

# Analyze the document
poller = client.begin_analyze_document(model_type, pdf_bytes)
result = poller.result()

# Output the results
with open("output.txt", "w", encoding="utf-8") as output_file:
    # Extract and print text
    for idx, page in enumerate(result.pages):
        output_file.write(f"Page {idx + 1}:\n\n")
        print(f"Page {idx + 1}:")
        for line in page.lines:
            print("...Line:", line.content)
            output_file.write(f"{line.content}\n")
        for selection_mark in page.selection_marks:
            print(f"Selection mark state: {selection_mark.state}")

    for kv_pair in result.key_value_pairs:
        if kv_pair.value:
            print(f"Key: {kv_pair.key.content}, Value: {kv_pair.value.content}")
    
    for table in result.tables:
        print(f"Table: {table.row_count}x{table.column_count}")
        for cell in table.cells:
            print(f"Cell: {cell.content}")

        output_file.write("\n=======================================================\n")
        print("\n")

# Save full results of Doc Intelligence
result_dict = result.to_dict()

# Serialize the result dictionary to JSON
json_result = json.dumps(result_dict, indent=4)

# Write the JSON result to a file
with open("output-full.json", "w") as output_file:
    output_file.write(json_result)

# Calculate script run time and print    
end_time = time.time()
total_time = end_time - start_time
print(f"Total script run time: {total_time} seconds")
