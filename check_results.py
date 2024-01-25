import unicodedata
import re

ANSWER_DIR_PATH = '/home/nickschiell/storage/DolloramaData/Transcripts/TestData/Answers/Bloomberg/'

#ANSWER_DIR_PATH = '/home/nickschiell/storage/DolloramaData/Transcripts/TestData/Answers/Refinitiv/'

RESULTS_DIR_PATH = './output/testResults'

BLOOMBERG_FILE_NAME_LIST = ['Barry_Larson_Frontera_Energy_Corp_0.txt',      
                            'Ken_Zinger_CES_Energy_Solutions_Corp_0.txt',      
                            'Shaun_Maine_Converge_Technology_Solutions_Corp_0.txt',
                            'Christian_Milau_Equinox_Gold_Corp_0.txt',      
                            'Michael_D._Garcia_Algoma_Steel_Group_Inc_0.txt',  
                            'John_Cassaday_Corus_Entertainment_Inc_0.txt',  
                            'Rod_Graham_Dexterra_Group_Inc_0.txt']
       
REFINITIV_FILE_LIST = [ 'Ammar_Al-Joundi_Agnico_Eagle_Mines_Limited_-_CEO_&_Non-Independent_Director_Agnico_Eagle_Mines_Ltd_Earnings_Call_0.txt',
                        'Armin_Martens_Artis_Real_Estate_Investment_Trust_-_President_&_CEO_Artis_Real_Estate_Investment_Trust_Earnings_Call_0.txt',
                        'Brian_James-Beaumont_Hill_Aritzia_Inc._-_Founder,_CEO_&_Chairman_Aritzia_Inc_Earnings_Call_0.txt',
                        'Clive_Thomas_Johnson_B2Gold_Corp._-_President,_CEO_&_Director_B2Gold_Corp_Earnings_Call_0.txt',
                        'Michael_R._Emory_Allied_Properties_Real_Estate_Investment_Trust_-_President,_CEO_&_Trustee_Allied_Properties_Real_Estate_Investment_Trust_0.txt',
                        'Miguel_Martin_Aurora_Cannabis_Inc._-_CEO_&_Director_Aurora_Cannabis_Inc_Earnings_Call_0.txt',
                        'Mike_Pearson_Valeant_Pharmaceuticals_International,_Inc._-_Chairman,_CEO_Valeant_Pharmaceuticals_International_Inc_Earnings_0.txt',
                        'Rod_Antal_Alacer_Gold_Corp._-_CEO_Alacer_Gold_Corp_Earnings_Conference_Call_0.txt',
                        'Terry_Anderson_ARC_Resources_Ltd._-_President_&_CEO_ARC_Resources_Ltd_Earnings_Call_0.txt',
                        'Terry_Booth_Aurora_Cannabis_Inc.txt',
                        'Victor_Neufeld_Aphria_Inc._-_Chair_of_the_Board_of_Directors,_CEO_&_President_Aphria_Inc_Earnings_Call_0.txt']
       
            
REGEX_PATTERN = '[^0-9a-zA-Z]+'

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def find_sub_list(sub_list : list,
                  full_list : list) -> list:
    """find occurances of sub_list in full_list

    Args:
        sub_list (list): the list being searched for
        full_list (list): the list being searched

    Returns:
        list: indices of the first element of the sub_list found in the full_list
    """

    idx_list = []

    full_list_length = len(full_list)
    sub_list_length = len(sub_list)

    for idx in range(full_list_length - sub_list_length + 1):
        if full_list[idx: idx + sub_list_length] == sub_list:
            idx_list.append(idx)

    return idx_list

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def is_sublist_unique(sub_list : list,
                      full_list : list) -> bool:
    """determine if sub_list is present and unique in full_list

    Args:
        sub_list (list): list being searched for
        full_list (list): list being searched

    Returns:
        bool: returns true if the sub_list is present and unique in the full_list
    """
    is_unique = False

    idx_list =  find_sub_list(sub_list, full_list)

    if len(idx_list) == 1:
        is_unique = True

    return is_unique

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def get_unique_list_token(input_list) -> list:
    """starting from the first entry in input_list this function
        builds the longest unique sub_list from input_list

    Args:
        input_list (_type_): list used to generate the longest unique sublist

    Returns:
        list: unique sub_list
    """
    token_length = 0
    keep_going = True
    sub_list = []

    while keep_going:
        token_length = token_length + 1

        sub_list = input_list[0:token_length]

        if is_sublist_unique(sub_list, input_list):
            keep_going = False

    return sub_list

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def get_residuals(list_1 : list, 
                  list_2 : list) -> (list, list):
    
    residual_1 = []
    residual_2 = list_2
    
    for item in list_1:
        
        if item in residual_2:
            residual_2.remove(item)
        else:
            residual_1.append(item)

    return residual_1, residual_2

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def compare_lists(list_1 : list,
                  list_2 : list) -> (list, list):
    """ compares two lists which are globally different but locally similar. ie each
    list contains sublists which are the same, but located in different sections.  

    Args:
        list_1 (list): first list to be compared
        list_2 (list): second list to be compared
    """

    list_1_missed = []

    while len(list_1) > 0:

        # starting at the beginning of list_1 find the longest unique sublist
        unique_sub_list = get_unique_list_token(list_1)
        
        # find instances of the unique sublist in list_2
        idx_list = find_sub_list(unique_sub_list, list_2)

        # if list 2 does not contain the unique sublist
        if  len(idx_list) == 0:
            list_1_missed = list_1_missed + unique_sub_list
        else:
            idx = idx_list[0]
            list_2 = list_2[0:idx]+list_2[idx+len(unique_sub_list):]

        list_1 = list_1[len(unique_sub_list):]   
    
    return get_residuals(list_1_missed, list_2)


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def clean_text(input_string : str) -> str:
    output_string = re.sub(REGEX_PATTERN, ' ', input_string)

    output_string = output_string.lower()

    return  output_string.strip()

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def file_to_string(file_path : str) -> str:

    text = ''
    
    try: 
        with open(file_path, 'r') as input_file:
            text = input_file.read()
            
        text = text.replace('\n', ' ')
        text = ' '.join(text.split())
    
        text = unicodedata.normalize("NFKD", text).strip()
    
    except UnicodeDecodeError as e:
        print(e)
        print(file_path)
   
    return text

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

file_list = REFINITIV_FILE_LIST
file_list = BLOOMBERG_FILE_NAME_LIST

for i, file_name in enumerate(file_list):    

    answers = file_to_string(ANSWER_DIR_PATH+file_name)
    results = file_to_string(RESULTS_DIR_PATH+file_name)
    
    answers_list = answers.split(' ')
    results_list = results.split(' ')

    residual_1, residual_2 = compare_lists( answers_list,
                                            results_list)
    
    print(f'{i+1}\t{len(residual_1)}\t{len(residual_2)}')   
    print(len(results_list),RESULTS_DIR_PATH+file_name) 
    print(len(answers_list),ANSWER_DIR_PATH+file_name) 
    input('Press ENTER to continue...')