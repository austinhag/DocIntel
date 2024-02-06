from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

# Import endpoints and api key
from env import azure_endpoint, api_key

# Path to PDF file
pdf_path = "sample2_medical_report.pdf"

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
        output_file.write("\n=======================================================\n")
        print("\n")

