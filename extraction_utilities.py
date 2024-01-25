import math

import fitz
from dataclasses import dataclass, field
from typing import List

from processed_document import ProcessedDocument

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

QA_HEADINGS = ['Question & Answer',
              'Question And Answer', 
              'Q&A', 
              'Questions And Answers', 
              'Questions & Answers', 
              '(Question & Answer)',
              '(Questions & Answers)',
              '(Question and Answer)',
              '(Question And Answer)',
              '(Questions and Answers)',
              'QUESTIONS AND ANSWERS',
              'QUESTION AND ANSWER',
              'QUESTION & ANSWER']

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@dataclass
class AnalysisResults:
    """
    Data class to hold the results of the analysis
    """

    file_path : str = ''
    company_name: str = ''
    report_year : int = 0
    participants_text_box_start : int = -1
    participants_text_box_end : int = -1
    ceo_name : str = ''
    num_ceos : int = 0
    qa_section_page: int = -1
    answer_text : List = field(default_factory=lambda: [])

    heading_font_dict : dict = field(default_factory=lambda: {})

    @property
    def num_answers(self) -> int:
        """property to return the number of answers found

        Returns:
            int: number of elements in the answer list
        """
        return len(self.answer_text)

    def __str__(self):
        return  f'{self.ceo_name}, {self.num_ceos}, {self.company_name}, ' \
                f'{self.num_answers}, {self.qa_section_page}'

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def get_processed_doc_from_fitz_doc(fitz_doc : fitz.fitz.Document) -> ProcessedDocument:
    """gets the text_blocks out of a fitz document and stores them in a ProcessedDocument

    Args:
        fitz_doc (fitz.fitz.document): document object containing the text blocks

    Returns:
        ProcessedDocument: Dataclass containing the extracted text_blocks
    """
    processed_document = ProcessedDocument()

    for page_num , page in enumerate(fitz_doc):

        blocks = page.get_text("dict", flags=11, sort=True)["blocks"]

        processed_document.add_text_blocks(blocks, page_num)

    return processed_document

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def get_processed_doc_from_file(file_path : str) -> ProcessedDocument:
    """ returns the text_blocks from a single pdf

    Args:
        file_path (str): file path to the pdf

    Returns:
        list: List of lists of text_block tuples
    """
    processed_document = ProcessedDocument()

    try:
        fitz_doc = fitz.open(file_path)
        processed_document = get_processed_doc_from_fitz_doc(fitz_doc)
        processed_document.file_path = file_path
    except fitz.fitz.FileDataError:
        print('Can not open file: ', file_path)

    return processed_document

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def flags_decomposer(flags):
    """Make font flags human readable."""
    l = []
    if flags & 2 ** 0:
        l.append("superscript")
    if flags & 2 ** 1:
        l.append("italic")
    if flags & 2 ** 2:
        l.append("serifed")
    else:
        l.append("sans")
    if flags & 2 ** 3:
        l.append("monospaced")
    else:
        l.append("proportional")
    if flags & 2 ** 4:
        l.append("bold")
    return ", ".join(l)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def calc_min_prev_dist( tb_target : tuple,
                        tb_test : tuple) -> float:

    return math.dist( [tb_test.x_2, tb_test.y_1],
                      [tb_target.x_1, tb_target.y_1])
    
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def get_previous_text_block(target_text_block : tuple,
                            text_blocks : list) -> tuple:
    
    min_dist = 1000.
    neareat_text_box_idx = 0
    
    for idx, text_box in enumerate(text_blocks):
    
        dist = calc_min_prev_dist(tb_target=target_text_block,tb_test=text_box)
        
        if(dist < min_dist):
            min_dist = dist
            neareat_text_box_idx = idx

    return text_blocks[neareat_text_box_idx]

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def only_block_on_line( target_block : tuple,
                        text_blocks : list) -> bool:
    is_only_block = True
    
    for block in text_blocks:
            
        # skip this block if it is the same as the target_block
        if target_block.x_1 == block.x_1 and target_block.y_1 == block.y_1:
            continue
            
        if block.y_1 == target_block.y_1 and block.y_2 == target_block.y_2:
            is_only_block = False
            break

    return is_only_block

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def view_pdf_data(fitz_doc : fitz.fitz.Document) -> None:
    """_summary_

    Args:
        doc (_type_): _description_
    """
    for page in fitz_doc:

        blocks = page.get_text("dict", flags=11, sort=True)["blocks"]

        for b in blocks: 
            # each block has keys ['number', 'type', 'bbox', 'lines']
            print('Block #:', b['number'], b['bbox'])
            for l in b["lines"]:  
                # each line has keys ['spans', 'wmode', 'dir', 'bbox']
                for s in l["spans"]: 
                    # each span has keys [  'size', 'flags', 'font', 'color',
                    #                       'ascender', 'descender', 'text',
                    #                       'origin', 'bbox']
                    font_name = s['font']
                    font_size = s['size']
                    font_colour = s['color']
                    font_flags = flags_decomposer(s["flags"])
                    line_text = s['text']

                    print(f'Text: {line_text}')
                    print(f'Font: {font_name}, size {font_size}, color {font_colour},  [{font_flags}]')
                    print('')

        print('~'*50)
        