import os
from langchain_openai import ChatOpenAI
from langchain_community.callbacks import get_openai_callback
from PyPDF2 import PdfReader
import pandas as pd

from secret_key import openapi_key
os.environ['OPENAI_API_KEY'] = openapi_key

def extract_resume_info(resume_path):
    resumeText = " "
    pdf_reader = PdfReader(resume_path)
    for page in pdf_reader.pages:
        resumeText += page.extract_text() 
    
    llm = ChatOpenAI(temperature=0.2)
    
    with get_openai_callback() as cb:
        prompt = f"Extract the following information from the resume given below: Name, Email, Contact Info,  Website links, Education, Skills, Experience, Projects, Additional Info. Resume : {resumeText}"
        
        messages = [
            ("system", " Answer the following question with the given information. Use a \n only after every section. If you do not know the answer, say null"),
            ("human", prompt)]
        
        resumeResponse = llm.invoke(messages)
        print(cb)
    #print(resumeResponse.content)
    
    parts = resumeResponse.content.split('\n')
    print(parts)
    
    if 'Skills:' in parts:
        start_index = parts.index('Skills:')
        if 'Experience:' in parts:
            stop_index = parts.index('Experience:')
            sublist = parts[start_index:stop_index]
        else:
            sublist = parts[start_index:]
        print("SUBLIST:", sublist)
        
        skills = ', '.join(sublist)
    else:
        # If "Skills:" not found, search for a substring containing "Skills"
        sublist = [element for element in parts if 'Skills' in element]
        if sublist:
            skills = ', '.join(sublist)
        else:
            skills = ''
    print(skills)
    
    # extracted_info = {}
    # for part in parts:
    #     part = part.strip()
    #     if part:
    #         key_value = part.split(':')
    #         if len(key_value) == 2:
    #             key = key_value[0].strip() 
    #             value = key_value[1].strip()  
    #             extracted_info[key] = value
                
    # print(extracted_info)
    
    # skills = extracted_info.get('Skills', '')
    return resumeResponse.content, skills


def skills_matching(resume_skills, skills_df):
    primary_skills = set(skills_df['Primary'].str.split(',').explode().str.strip())
    secondary_skills = set(skills_df['Secondary'].str.split(',').explode().str.strip())
    resume_skills_list = resume_skills.split(',')
    
    llm = ChatOpenAI(temperature=0.2)
    
    with get_openai_callback() as cb:
    
        # Calculate similarity scores for primary skills
        prompt1 = f"Find the intersection between set 1 : {', '.join(resume_skills_list)} and set 2 : {primary_skills}. Give me a percentage as (intersection/number of items in set 2)*100."  
        
        messages = [
            ("system", "Answer the following question with a percentage as an answer. Do not give any further explanations. Output the percentage without the % sign. If you do not know the answer, say 0"),
            ("human", prompt1)]
        
        primary_similarity_scores = llm.invoke(messages)
        print("Primary Skills Match :" , primary_similarity_scores.content)
        
        
        # Calculate similarity scores for secondary skills
        prompt2 = f"Find the intersection between set 1 : {', '.join(resume_skills_list)} and set 2 : {secondary_skills}. Give me a percentage as (intersection/number of items in set 2)*100."  
        
        messages = [
            ("system", "Answer the following question with a percentage as an answer. Do not give any further explanations. Output the percentage without the % sign. If you do not know the answer, say 0"),
            ("human", prompt2)]
        
        secondary_similarity_scores = llm.invoke(messages)
        print("Secondary Skills Match :" , secondary_similarity_scores.content) 
        
        print(cb)
    
    return primary_similarity_scores.content, secondary_similarity_scores.content

    
def jobDescription_matching(resume_response, job_description_path):
    llm = ChatOpenAI(temperature=0.2)
    
    jobDescription = " "
    pdf_reader = PdfReader(job_description_path)
    for page in pdf_reader.pages:
        jobDescription += page.extract_text() 
    
    prompt = f"Give the job fit as a percentage for the job description : {jobDescription} and the given resume : {resume_response}."

    messages = [
        ("system", "Answer the following question with a percentage as an answer. Do not give any further explanations. Output the percentage without the % sign. If you do not know the answer, say 0"),
        ("human", prompt)]
    
    jobDescription_matching_score = llm.invoke(messages)
    print("Job Description Matching Score :" , jobDescription_matching_score.content)
    
    return jobDescription_matching_score.content

resume_path = '/Users/reethu/coding/Projects/AI_Recruiter/ResumeScoring/sample/Reethu_Resume.pdf'
response, resume_skills = extract_resume_info(resume_path)

skills_df = pd.read_csv('/Users/reethu/coding/Projects/AI_Recruiter/ResumeScoring/skills.csv')
primarySkillScore, secondarySkillScore = skills_matching(resume_skills, skills_df)

job_description_path = '/Users/reethu/coding/Projects/AI_Recruiter/ResumeScoring/Job_Description.pdf'
jobDescriptionScore = jobDescription_matching(response, job_description_path)

total_score = float(primarySkillScore) + float(secondarySkillScore) + float(jobDescriptionScore)
print("Total score : ", total_score)