import os
from langchain.llms import OpenAI
from langchain.chains.question_answering import load_qa_chain
from langchain.schema.document import Document
from PyPDF2 import PdfReader

from secret_key import openapi_key
os.environ['OPENAI_API_KEY'] = openapi_key

def extract_resume_info(resume_path):
    # Create a PdfReader object
    text = " "
    docs = []
    pdf_reader = PdfReader(resume_path)
    for page in pdf_reader.pages:
        text += page.extract_text() 
        docs.append(Document(page_content=text))
    
    prompt_template = """
        Extract the following information from the resume:
        
        Name: {}
        Email: {}
        Contact Info: {}
        Education: {}
        Skills: {}
        Experience: {}
        Job Title/Designation: {}
    """
    
    llm = OpenAI()
    chain = load_qa_chain(llm, chain_type="stuff",verbose=True)
    response = chain.run(input_documents=docs, question=prompt_template)
    
    print(type(response))
    return response

resume_path = '/Users/reethu/coding/Projects/AI_Recruiter/ResumeScoring/sample/Dhaval_Thakkar_Resume.pdf'
resume_info = extract_resume_info(resume_path)
print(resume_info)