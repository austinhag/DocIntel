from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import json

# Import endpoints and api key
from env import azure_endpoint, api_key

# Path to PDF file
pdf_path = "sample2_medical_report.pdf"
pdf_path = "HISTOPATHOLOGY-COLONOSCOPY-WITH-POLYPECTOMY-BIOPSY-report-format-example-sample-template-Drlogy-lab-report.pdf"

# Create Doc Intelligence Client
client = DocumentAnalysisClient(azure_endpoint, AzureKeyCredential(api_key))

# Read the PDF file
with open(pdf_path, "rb") as pdf_file:
    pdf_bytes = pdf_file.read()

# Analyze the document
poller = client.begin_analyze_document("prebuilt-document", pdf_bytes)
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
    
