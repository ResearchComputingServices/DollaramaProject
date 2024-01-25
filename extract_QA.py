import glob
import os
import time
import random

import concurrent.futures

from extract_QA_bloomberg import process_bloomberg_doc
from extract_QA_refinitiv import process_refinitiv_doc
from extraction_utilities import get_processed_doc_from_file, AnalysisResults, ProcessedDocument

OUTPUT_PATH = './output'
    
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def get_data_file_paths() -> list:
    """finds all the pdfs in a directory tree

    Returns:
        list: a list of file paths to the pdfs found
    """
    
    #base_data_dir = '/home/nickschiell/storage/DolloramaData/Transcripts/Refinitiv'
    #base_data_dir = '/home/nickschiell/storage/DolloramaData/Transcripts/Bloomberg'
    base_data_dir = '/home/nickschiell/storage/DolloramaData/Transcripts'
    
    data_file_paths = []

    for file_path in glob.glob(base_data_dir+'/**/*.pdf', recursive=True):
        data_file_paths.append(file_path)

    return data_file_paths

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def get_file_paths_from_file() -> list:
    
    file_paths = []
    
    input_file = open('./docs/success_no_ceo_name.txt', 'r')
    lines = input_file.readlines()
    
    for line in lines:
        file_paths.append(line.strip())
        
    return file_paths

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def get_processed_documents(file_paths : list) -> list:
    
    """given a list of file paths this will extract all the 
    text_blocks from there

    Args:
        file_paths (list): list of file paths to pdf documents

    Returns:
        list: list of list of text_blocks
    """
    processed_documents = []

    with concurrent.futures.ProcessPoolExecutor(max_workers=30) as executor:

        future_results = [executor.submit(get_processed_doc_from_file, fp) for fp in file_paths]
        for finished in concurrent.futures.as_completed(future_results):
            processed_documents.append(finished.result())

    return processed_documents

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def get_analysis_results(processed_documents : list,
                         company_ceo_dict : dict) -> list:
    """give a list of list of texblocks for a single document this function
    performs the analysis to extract the required data

    Args:
        processed_documents (list): _description_

    Returns:
        list: _description_
    """

    results = []

    for processed_doc in processed_documents:
  
        result = None

        if "Refinitiv" in processed_doc.file_path:
            result = process_refinitiv_doc(processed_doc)
        else:
            result = process_bloomberg_doc(processed_doc,company_ceo_dict)
        
        if result is not None:
            results.append(result)
            
    return results

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def generate_file_name(result : AnalysisResults,
                       output_dir_path : str) -> str:
    """_summary_

    Args:
        result (AnalysisResults): _description_
        output_dir_path (str): _description_

    Returns:
        str: _description_
    """
    
    file_exists = True
    file_counter = 0
    file_path = ''
    
    while file_exists:
                
        file_name = f'{result.ceo_name}_{result.company_name}_{result.report_year}_{file_counter}.txt'
        
        file_name = file_name.replace(' ', '_')
        file_name = file_name.replace('/','_')

        file_path = os.path.join(output_dir_path, file_name)

        file_exists = os.path.isfile(file_path)
        file_counter = file_counter + 1
                  
    return file_path 
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def save_to_file(results : list,
                 output_dir_path: str) -> None:
    """Save analysis results to files in a given directory

    Args:
        results (list): list of AnalysisResults objects
        output_dir_path (str): path to output directoy
    """

    for result in results:

        file_path = generate_file_name(result, output_dir_path)
        try:
            with open(file_path, 'w+', encoding='UTF-8',) as out:
                for answer in result.answer_text:
                    out.write(answer+'\n')
        except FileNotFoundError:
            print(f'Could NOT save file: {file_path}')

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def display_results(results : list) -> None:
   
    num_no_ceo = 0
    num_multiple_ceo = 0
    num_year_range = 0
    num_no_answer = 0
    num_success = 0
   
    with open('results_table.dat', 'w+', encoding='UTF-8') as output_file:
        for num, result in enumerate(results):
            status = ''

            if result.num_ceos == 0:
                status = 'No CEO'
                num_no_ceo = num_no_ceo + 1
            elif result.num_ceos > 1:
                num_multiple_ceo =  num_multiple_ceo + 1
                status = 'Multiple CEOs'
            elif result.num_ceos == 1 and result.num_answers == 0:
                status = 'No Answers'
                num_no_answer = num_no_answer + 1
            else:
                status = 'Success'
                num_success = num_success + 1
        
            row = f'{num}+{status}+{result.company_name}+{result.report_year}+{result.ceo_name}+{result.num_ceos}+{result.num_answers}+{result.file_path}'

            output_file.write(row+'\n')
                        
        print(  f'num_year_range: {num_year_range}\n'
                f'num_no_ceo: {num_no_ceo}\n' 
                f'num_multiple_ceo: {num_multiple_ceo}\n'
                f'num_no_answer: {num_no_answer}\n'
                f'num_success: {num_success}')
        
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def read_ceo_file() -> dict:
    input_file = open('./docs/company_name_ceo.csv', 'r')
    lines = input_file.readlines()
    
    all_companies_dict = {}
    
    keys = lines[0].split('+')[2:]
    
    for idx,key in enumerate(keys):
        keys[idx] = key.strip()
    
    for line in lines[1:]:
        company_name = line.split('+')[1]
        line_split = line.split('+')[2:]
        
        company_dict = {}

        for idx, name in enumerate(line_split):
            if idx < len(keys):
                company_dict[keys[idx]] = name.strip()
        
        all_companies_dict[company_name] = company_dict
        
    return all_companies_dict


def main():
    """
    Main function for running the QA extraction pipeline in parallel
    """
    start_time_point = time.time()

    company_ceo_dict = read_ceo_file()

    # get all the file_paths
    file_paths = get_data_file_paths()

    # file_paths = get_file_paths_from_file()
    print(f'# of files: {len(file_paths)}')

    # open all the files with fitz and get there text_blocks in order
    processed_documents = get_processed_documents(file_paths)

    print(f'# of processed docs: {len(processed_documents)}')

    # search the text_blocks for data we are interested in
    results = get_analysis_results(processed_documents,company_ceo_dict)

    end_time_point = time.time()
    print(f'Total : {end_time_point - start_time_point}')
    
    # print('saving')
    save_to_file(results, OUTPUT_PATH)
    display_results(results)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if __name__ == '__main__':
    main()
