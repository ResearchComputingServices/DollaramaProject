from dataclasses import dataclass, field
from typing import List

from unidecode import unidecode

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@dataclass
class DocumentLine:
    """
    Data class representing a line extacted using fitz. Contains text and font data
    """
    text : str = ''
    font_dict :  dict = field(default_factory= lambda: {})
    font_style : List = field(default_factory=lambda: [])

    def __init__(self,
                 init_dict : dict):

        self.text = unidecode(init_dict['text'])

        self.font_dict = {}
        self.font_dict['name'] = init_dict['font']
        self.font_dict['size'] = init_dict['size']
        self.font_dict['colour'] = init_dict['color']

    def __str__(self):
        return  f'Text: {self.text} \n' \
                f'Font: {self.font_name}, size {self.font_size}, color {self.font_colour}'
    
    @property
    def font_name(self) -> str:
        return self.font_dict['name']
    
    @property
    def font_size(self) -> str:
        return self.font_dict['size']
    
    @property
    def font_colour(self) -> str:
        return self.font_dict['colour']
     
    def contains_text(self, token : str) -> bool:
        if token in self.text:
            return True
        else:
            return False
        
    def contains_font(self, font_dict : dict) -> bool:
        
        input_keys = font_dict.keys()
        
        for input_key in input_keys:
            if font_dict[input_key] != self.font_dict[input_key]:
                return False
        
        return True        
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@dataclass
class DocumentTextBlock:
    """
    Text_block extracted from pdf using fitz
    """
    lines : List = field(default_factory=lambda: [])
    x_1 : float = 0.
    y_1 : float = 0.
    x_2 : float = 0.
    y_2 : float = 0.
    page_number : int = -1

    def __init__(self,
                 init_dict : dict,
                 page_number : int):

        self.x_1 = init_dict['bbox'][0]
        self.y_1 = init_dict['bbox'][1]
        self.x_2 = init_dict['bbox'][2]
        self.y_2 = init_dict['bbox'][3]
        
        self.page_number = page_number
        
        self.lines = []
        for line in init_dict['lines']:
            for span in line['spans']:
                self.lines.append(DocumentLine(span))

    def __str__(self):
        ret_str =  f'Page #{self.page_number} \n ({self.x_1}, {self.y_1}), ({self.x_2}, {self.y_2})\n' 
        for line in self.lines:
            ret_str = ret_str + line.__str__() +'\n'

        return ret_str

    @property
    def num_lines(self) -> int:
        return len(self.lines)

    def get_text(self) -> str:
        """get all the text contained in lines

        Returns:
            str: all text contained in lines
        """
        text = ''
        for line in self.lines:
            text = text + line.text + '\n'

        return text.strip()
    
    def contains_text(self, token : str) -> bool:
        """check if token in contained in text_block

        Args:
            token (str): _description_

        Returns:
            bool: _description_
        """
        for line in self.lines:
            if line.contains_text(token):
                return True

        return False
    
    def contains_font(self, font : dict) -> bool:

        for line in self.lines:
            if line.contains_font(font):
                return True

        return False

    def contains_section(   self,  
                            title : str,
                            font : dict) -> bool:
        """check if token in contained in text_block

        Args:
            token (str): _description_

        Returns:
            bool: _description_
        """
        for line in self.lines:
            if line.contains_text(title) and line.contains_font(font):
                return True

        return False
    
    def get_line_font(self,
                      idx : int = 0) -> dict:
        
        font_dict = {}
        
        if idx < len(self.lines):
            font_dict = self.lines[idx].font_dict

        return font_dict
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@dataclass
class ProcessedDocument:
    """
    dataclass representing the data extracted from a pdf by fitz
    """
    document_text_blocks :  List = field(default_factory=lambda: [])

    file_path : str = ''

    @property
    def num_text_blocks(self) -> int:
        """returns the number of elements in the document_text_blocks list

        Returns:
            int: # of elements in self.document_text_blocks
        """
        return len(self.document_text_blocks)

    def add_text_block(self,
                       text_block : DocumentTextBlock,
                       page_number : int) -> None:
        """Add a text block to the document

        Args:
            text_block (DocumentTextBlock): text block to be added
        """

        self.document_text_blocks.append(DocumentTextBlock(text_block, page_number))

    def add_text_blocks(self,
                        text_blocks : list,
                        page_number : int) -> None:
        """Add a list of text blocks to the document

        Args:
            text_blocks (list): text blocks to be added
        """
        for text_block in text_blocks:
            self.add_text_block(text_block,page_number)

    def get_text(   self,
                    start_idx : int,
                    end_idx : int) -> str:

        text = ''
        
        for text_block in self.document_text_blocks[start_idx:end_idx]:
            text = text + text_block.get_text() + '\n'
        
        return text
    
    def get_text_blocks(self,
                        start_idx : int,
                        end_idx : int) -> list:

        if end_idx > self.num_text_blocks:
            end_idx = self.num_text_blocks
        
        return self.document_text_blocks[start_idx:end_idx]

    def get_text_block(self,
                        idx : int) -> DocumentTextBlock:

        if idx > self.num_text_blocks:
            idx = self.num_text_blocks
        
        return self.document_text_blocks[idx]

    def get_heading_idx(self,
                        titles : list,
                        font_dict: dict,
                        start_idx = -1,
                        end_idx = -1) -> int:
        """find the section heading

        Args:
            title (str): title of section
            font (str): font type used in headings

        Returns:
            int: index of text_block containing the heading
        """

        if start_idx == -1:
            start_idx = 0
        if end_idx == -1:
            end_idx = self.num_text_blocks

        for idx, text_block in enumerate(self.document_text_blocks[start_idx:end_idx]):
            for title in titles:
                if text_block.contains_section(title, font_dict):
                    return idx+start_idx

        return -1

    def get_next_heading_idx(self,
                             start_idx : int,
                             font: dict) -> int:
        """_summary_

        Args:
            start_idx (int): _description_
            font (dict): name, colour, size

        Returns:
            int: _description_
        """
        
        for idx, text_block in enumerate(self.document_text_blocks[start_idx:]):
            if text_block.contains_font(font):
                return idx + start_idx
        
        return -1
    
    def display(self, 
                page_number = -1):
        
        for block_num , text_block in enumerate(self.document_text_blocks):
            if page_number < 0:
                print(block_num, text_block)
            else:
                if text_block.page_number == page_number:
                    print(block_num, text_block)