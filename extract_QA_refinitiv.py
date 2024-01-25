import fitz
import glob
import re
import math 
import unicodedata
from difflib import SequenceMatcher

from extraction_utilities import AnalysisResults, QA_HEADINGS
from processed_document import ProcessedDocument

REGEX_CLEAN_UP_PATTERN = '[^0-9a-zA-Z\s]+'
REGEX_COMPANY_NAME_PATTERN = 'Q[0-9] 2([0-9]*)'

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def text_contains(  text : str,
                    tokens : list,
                    exact_match = False) -> bool:
    """determins if the string 'token' is contained in the text box.

    Args:
        text_box (str): corpus being searched
        tokens (list): list of strings which are being searched for

    Returns:
        bool: True if token in text_box
    """

    token_found = False

    # replace ligature with ascii characters
    cleaned_text = unicodedata.normalize("NFKD", text)
    cleaned_text = re.sub(REGEX_CLEAN_UP_PATTERN, '', cleaned_text)
    
    for token in tokens:

        if exact_match:
            if token.lower() == cleaned_text.lower().strip():
                token_found = True
        else:
            search_pattern = r'\b' + token + r'\b'
            matches = re.findall(search_pattern, cleaned_text.strip())
            
            if len(matches) > 0:
                token_found = True

    return token_found

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def calc_min_prev_dist( tb_target : tuple, 
                        tb_test : tuple) -> float:

    return math.dist( [tb_test[2], tb_test[1]],
                      [tb_target[0], tb_target[1]])
    
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def get_previous_text_bock(target_text_block : tuple,
                           text_blocks : list) -> tuple:
    
    min_dist = 1000.
    neareat_text_box_idx = -1
    
    for idx, text_box in enumerate(text_blocks):
        dist = calc_min_prev_dist(tb_target=target_text_block,tb_test=text_box)
        
        if(dist < min_dist):
            min_dist = dist
            neareat_text_box_idx = idx

    return text_blocks[neareat_text_box_idx]

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def detect_heading_font(processed_doc : ProcessedDocument,
                         results : AnalysisResults) -> None:

    for block in processed_doc.document_text_blocks:

            if block.page_number == 1:
                heading_idx = processed_doc.get_heading_idx(['CORPORATE PARTICIPANTS'], {})
                
                heading_text_block = processed_doc.get_text_block(heading_idx)
                results.heading_font_dict = heading_text_block.get_line_font()
                
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def extract_company_name(processed_doc : ProcessedDocument,
                         results : AnalysisResults) -> bool:
    """Extracts the company name from the header

    Args:
        processed_doc (ProcessedDocument): document being looked at
        results (AnalysisResults): data class containing results

    Returns:
        bool: True if company name found
    """
    found = False
    results.company_name = 'UNKNOWN'

    for block in processed_doc.document_text_blocks:

        if block.page_number == 0:
            
            for line in block.lines:
                match = re.findall(REGEX_COMPANY_NAME_PATTERN, line.text)
                if len(match) > 0:
                    results.company_name = re.sub(REGEX_COMPANY_NAME_PATTERN, '', line.text).strip()
                    results.report_year = line.text[3:7]
    
    return found

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def extract_ceo_name(processed_doc : ProcessedDocument,
                     results : AnalysisResults) -> bool:
    
    found = False

    # extract the "Company Participants" section text blocks
    start_idx = processed_doc.get_heading_idx(['CORPORATE PARTICIPANTS'], results.heading_font_dict)
    end_idx = processed_doc.get_next_heading_idx(start_idx+1, results.heading_font_dict)

    participants_section = processed_doc.get_text_blocks(start_idx,end_idx+1)

    # search the "Company Participants" section for the CEO name
    ceo_count = 0
    ceo_name = 'UNKNOWN'

    for block in participants_section:
        for line in block.lines:
            if text_contains(line.text,['CEO','Chief Executive Officer']):
                ceo_count = ceo_count + 1
                ceo_name = block.get_text().replace('\n', ' ')
   
    # clean up the name
    ceo_name = unicodedata.normalize("NFKD", ceo_name).strip()

    # update results
    results.ceo_name = ceo_name
    results.num_ceos = ceo_count
    results.participants_text_box_start = start_idx
    results.participants_text_box_end = end_idx

    return found

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
REGEX_CLEANING_PATTERNS = [ 'REFINITIV STREETEVENTS',
                            'THOMSON REUTERS',
                            '©[0-9]+ Refinitiv',
                            '©[0-9]+ Thomson Reuters',
                            '[0-9][0-9], 20[0-9][0-9] [a-zA-Z0-9 /:,]+ Q[0-9] 20[0-9][0-9]']

def clean_answer_text(text_blocks : list) -> str:
    
    answer_text = ''

    for block in text_blocks:
        include = True 
        
        for pattern in REGEX_CLEANING_PATTERNS:
            matches = re.findall(pattern, block.get_text())
        
            if len(matches) > 0:
                include = False

        if include:
            answer_text = answer_text + block.get_text() + '\n'
       
    return answer_text

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def extract_answers(processed_doc : ProcessedDocument,
                    results : AnalysisResults) -> None:
    
    ceo_name = results.ceo_name.strip()

    qa_start_idx = processed_doc.get_heading_idx(QA_HEADINGS, results.heading_font_dict)
    qa_end_idx = processed_doc.num_text_blocks

    qa_section = processed_doc.document_text_blocks[qa_start_idx:qa_end_idx]
    results.qa_section_page = qa_section[0].page_number
    
    for idx in range(qa_start_idx, qa_end_idx):
        text_block = processed_doc.get_text_block(idx)

        # if the text is the entire ceo name then we have 
        if SequenceMatcher(None, text_block.get_text(), ceo_name).ratio() > 0.9:            
            end_idx = processed_doc.get_next_heading_idx(idx+1, text_block.get_line_font())

            answer_text = clean_answer_text(processed_doc.get_text_blocks(idx+1,end_idx))
            
            results.answer_text.append(answer_text)

            
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def process_refinitiv_doc(processed_doc : ProcessedDocument) -> AnalysisResults:
    """_summary_

    Args:
        doc (list): _description_

    Returns:
        AnalysisResults: _description_
    """
    results = AnalysisResults()
    results.file_path = processed_doc.file_path
    
    if processed_doc.num_text_blocks > 0:

        detect_heading_font(processed_doc, results)

        # Get the name of the company
        extract_company_name(processed_doc, results)

        # Get the name of the CEO from the first page
        extract_ceo_name(processed_doc, results)

        # now search pages for answers from the CEO
        extract_answers(processed_doc, results)
    else:
        print(f'File contained no data: {processed_doc.file_path}')

    return results
