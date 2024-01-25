import fitz
import re

import unicodedata

from extraction_utilities import only_block_on_line, get_previous_text_block
from extraction_utilities import AnalysisResults, QA_HEADINGS
from extraction_utilities import get_processed_doc_from_fitz_doc
from processed_document import ProcessedDocument

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def text_contains(  text : str,
                    tokens : list) -> bool:
    
    """determins if the string 'token' is contained in the text box.

    Args:
        text_box (str): corpus being searched
        tokens (list): list of strings which are being searched for

    Returns:
        bool: True if token in text_box
    """

    token_found = False

    # replace ligature with ascii characters
    cleaned_text = unicodedata.normalize("NFKD", text).strip()
    
    cleaned_text = cleaned_text.replace('(', '')
    cleaned_text = cleaned_text.replace(')', '')    
    cleaned_text = cleaned_text.replace('"', '')    
    cleaned_text = cleaned_text.replace('.', '') 
    cleaned_text = cleaned_text.replace('é', '') 
    
    for token in tokens:

        token = token.replace('(', '')
        token = token.replace(')', '')    
        token = token.replace('"', '') 
        token = token.replace('.', '') 
        token = token.replace('é', '') 
    
        search_pattern = r'\b' + token + r'\b'
        matches = re.findall(search_pattern, cleaned_text)

        if len(matches) > 0:
            token_found = True

    return token_found

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def text_matches(text: str,
                       tokens : list) -> bool:

    token_found = False

    # replace ligature with ascii characters
    cleaned_text = unicodedata.normalize("NFKD", text).strip()

    for token in tokens:

        if token == cleaned_text.strip():
            token_found = True

    return token_found

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def extract_company_name(processed_doc : ProcessedDocument,
                         results : AnalysisResults) -> None:
    """Extracts the company name from the header

    Args:
        processed_doc (ProcessedDocument): document being looked at
        results (AnalysisResults): data class containing results

    Returns:
        bool: True if company name found
    """

    results.company_name = 'UNKNOWN'
    results.report_year = 0

    for block in processed_doc.document_text_blocks:
        if block.contains_text('Company Name: '):
            split_block = block.get_text().split('\n')
            results.company_name = split_block[0].split(':')[1].strip()
        
        if block.contains_text('Date: '):
            split_block = block.get_text().split('\n')
            results.report_year = split_block[2].split(':')[1].split('-')[0].strip()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def extract_ceo_name(processed_doc : ProcessedDocument,
                     results : AnalysisResults) -> None:
    ceo_name = 'UNKNOWN'
    success = False
    # extract the "Company Participants" section text blocks
    start_idx = processed_doc.get_heading_idx(['Company Participants'], {'name':'AvenirNextPForBBG-Medium'})
    end_idx = processed_doc.get_next_heading_idx(start_idx+1, {'name':'AvenirNextPForBBG-Medium'})

    participants_section = processed_doc.get_text_blocks(start_idx,end_idx+1)

    # search the "Company Participants" section for the CEO name
    ceo_count = 0
       
    for block in participants_section:
        
        if text_contains(block.get_text(), ['CEO','Chief Executive Officer']):
            ceo_count = ceo_count + 1
            if only_block_on_line(block, participants_section):             
                ceo_name = block.get_text().split(',')[0]
            else:
                tb_ceo_name = get_previous_text_block(block, participants_section)
                ceo_name = tb_ceo_name.get_text().strip()
    # clean up the name
    ceo_name = unicodedata.normalize("NFKD", ceo_name)

    # update results
    if ceo_count == 1:
        results.ceo_name = ceo_name
        results.num_ceos = ceo_count
        results.participants_text_box_start = start_idx
        results.participants_text_box_end = end_idx
        success = True

    return success
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

REGEX_CLEANING_PATTERNS = ['{BIO [0-9]+ <GO>}',
                           'Page [0-9]+ of [0-9]+',
                           'Bloomberg Transcript',
                           'FINAL',
                           'Company Name: [a-zA-Z0-9 ]+',
                           'Company Ticker: [a-zA-Z0-9 ]+',
                           'Date: [a-zA-Z0-9- ]+']

def clean_answer_text(text_blocks : list) -> str:
    
    answer_text = ''

    for block in text_blocks:
        for line in block.lines:
            text = line.text
            
            for pattern in REGEX_CLEANING_PATTERNS:
                text = re.sub(pattern, ' ', text)

            answer_text = answer_text + text + '\n'
            
    return answer_text

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def extract_answers(processed_doc : ProcessedDocument, 
                    results : AnalysisResults) -> None:
    """_summary_

    Args:
        processed_doc (ProcessedDocument): _description_
        results (AnalysisResults): _description_
    """
    ceo_name = results.ceo_name

    qa_start_idx = processed_doc.get_heading_idx(QA_HEADINGS, {'name':'AvenirNextPForBBG-Medium'})
    qa_end_idx = processed_doc.num_text_blocks
    
    results.qa_section_page = processed_doc.get_text_block(qa_start_idx).page_number
    
    for idx in range(qa_start_idx, qa_end_idx):
        text_block = processed_doc.get_text_block(idx)
            
        if text_block.contains_section(ceo_name, {'name':'AvenirNextPForBBG-Medium'}):
            end_idx = processed_doc.get_next_heading_idx(idx+1, {'name':'AvenirNextPForBBG-Medium'})
            
            answer_text = clean_answer_text(processed_doc.get_text_blocks(idx+1,end_idx+1))
            
            results.answer_text.append(answer_text)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def process_bloomberg_doc(processed_doc : ProcessedDocument,
                          company_ceo_dict : dict) -> AnalysisResults:
    """_summary_

    Args:
        doc (list): _description_

    Returns:
        AnalysisResults: _description_
    """
    results = AnalysisResults()
    results.file_path = processed_doc.file_path
    
    if processed_doc.num_text_blocks > 0:

        # Get the name of the company
        extract_company_name(processed_doc, results)

        # Get the name of the CEO from the first page
        if not extract_ceo_name(processed_doc, results):
            if results.company_name in company_ceo_dict.keys():
                if results.report_year in company_ceo_dict[results.company_name].keys():
                    ceo_name = company_ceo_dict[results.company_name][results.report_year]
                    if ceo_name != '':
                        results.ceo_name =  ceo_name
                        results.num_ceos = 1

        # now search pages for answers from the CEO
        extract_answers(processed_doc, results)
       
    return results

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def process_bloomberg_file(file_path : str) -> AnalysisResults:
    """Perform complete analysis pipeline starting from a file path
       
    Args:
        file_path (str): file path to pdf

    Returns:
        AnalysisResults: results of analysis
    """
    results = AnalysisResults()

    # store the name of the file being processed
    results.file_path = file_path.split('/')[-1]

    try:
        fitz_doc = fitz.open(file_path)
        processed_doc = get_processed_doc_from_fitz_doc(fitz_doc)

        results = process_bloomberg_doc(processed_doc)

    except fitz.fitz.FileDataError:
        results.ceo_name = 'FAILED TO OPEN FILE'

    return results

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def main():
    """
    runs the compelte analysis pipeline on sameple data
    """

    bloomberg_list = []

    results = []

    for file_path in bloomberg_list:
        results = process_bloomberg_file(file_path)

    # display the results
    for result in results:
        print(result)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if __name__ == '__main__':
    main()
  
