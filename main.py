import re
import json
import dataclasses
from typing import Optional

import pandas as pd
from PyPDF2 import PdfReader

from utils import Logger

PDF_PATH = "./input/contacts.pdf"

CONTACTS_RE = r"\bCONTACT\b\s*\n*\s*(.+)"

ALT_CONTACTS_RE = r"CONTACTS\b\s*\n*\s*(.+)"

COMPANY_TITLES_RE = r"[^a-z]+?\d+\s*[a-zA-Z]\s*\d+"

COMPANY_NAME_RE = r"([^a-z]+?)\s*\d+\s*[a-zA-Z]\s*\d+"

COMPANY_TEL_RE = r"(?<!CONTACT).*?TEL\s*([+\(\)\d\s]+)"

COMPANY_EMAIL_RE = r"(?<!CONTACT).*?([\w\-\.*]+@\w+.\w{,5})"

MAIN_ACTIVITY_RE = r"MAIN\s*ACTIVIT\w{1,4}\s*\n*(.+?)MAIN\s*APPLICATION"

CONTACTS_SPLIT_RE = r"[\w\-\.*]+@\w+.\w{,5}[\s\n]*(.+?[\w\-\.*]+@\w+.\w{,5})"

WEBSITE_RE = r"(h?t?t?p?s?:?\/?\/?\b([^\s]{2,}\.[^\s]{2,}\.?\w*))"

COMPANIES_RE = r"[^a-z®]+?\d+\s*[a-zA-Z]\s*\d+.+?CONTACT.+?TEL.+?MAIN\s*ACTIVIT[Y|IES].+?MAIN\s*APPLICATION\s*SECTOR"

@dataclasses.dataclass
class Contact:
    name: str
    title: str
    email: str
    tel: str
    cell: str

@dataclasses.dataclass
class Company:
    company_name: str
    address: str = None
    company_tel: str = None
    website: Optional[str] = None
    company_email: Optional[str] = None
    contacts: list[Contact] = dataclasses.field(default_factory=list)
    main_activity: Optional[str] = None

class PDFExtractor:
    """Extracts company information from https://www.calameo.com/read/0040839447ed4c24114f7"""
    def __init__(self) -> None:
        self.logger = Logger(__class__.__name__)
        self.logger.info("{:*^50}".format("PDFExtractor Started"))

        self.companies: list[Company] = []

        self.reader = self.__read_pdf()
    
    @staticmethod
    def __read_pdf() -> PdfReader:
        return PdfReader(PDF_PATH)
    
    def __search(self,  
                 pattern: str,  
                 text: str,  flags: int=0, group: Optional[int]=0) -> Optional[str]:
        text_re = re.search(pattern, text.strip(), flags=flags)

        required_text = text_re.group(group) if text_re is not None else None

        return required_text
    
    def __findall(self,  pattern: str,  text: str,  flags: int=0) -> list[str]:
        return re.findall(pattern, text, flags=flags)
    
    @staticmethod
    def __escape_regex_characters(text: str) -> str:
        text = text.replace("\\", "\\\\").replace("+", "\+").replace("*", "\*").replace("?", "\?")

        text = text.replace("(", "\(").replace(")", "\)").replace("[", "\[").replace("]", "\]")

        return text
    
    @staticmethod
    def __asciify(text: str) -> str:
        if isinstance(text, str): return text.encode("ascii", errors="ignore").decode()
    
    def __split(self, company: str) -> list[str]:
        company_titles = self.__findall(COMPANY_TITLES_RE, company, re.DOTALL)

        companies = []

        if len(company_titles) > 1:
            for index, title in enumerate(company_titles):
                if title != company_titles[-1]:
                    pattern = rf"({title}.+){company_titles[index+1]}"

                    new_company = self.__search(pattern, company, re.DOTALL, 1)
                    
                else:
                    new_company = company.split(new_company)[-1]
                
                companies.append(new_company)
        
        else:
            companies.append(company)
        
        return companies
    
    @staticmethod
    def __strip(text: str|None) -> Optional[str]:
        if isinstance(text, str): return text.strip()
    
    def __process_company(self, company_text: str) -> None:
        if company_text is None: return

        name = self.__search(COMPANY_NAME_RE, company_text, re.DOTALL, 1)

        if name is None:
            self.logger.warn(f"No company name: \n {company_text}")

            return
        
        company = Company(company_name=self.__strip(name))

        escaped_name = self.__escape_regex_characters(name)

        pattern = r"\s*\d+\s*[a-zA-Z]\s*\d+\n*(.*?)?\nTEL"

        company.address = self.__search(pattern, company_text, re.DOTALL, 1)

        company.company_tel = self.__search(COMPANY_TEL_RE, company_text, re.DOTALL, 1)

        company.website = self.__search(WEBSITE_RE, company_text, re.DOTALL, 1)

        company.company_email = self.__search(COMPANY_EMAIL_RE, company_text, re.DOTALL, 1)

        main_activity = self.__search(MAIN_ACTIVITY_RE, company_text, re.DOTALL, 1)

        if main_activity is not None:
            company.main_activity = ", ".join(
                [a.strip()  for a in main_activity.split("• ") if a.strip()])

        contacts_text = self.__search(CONTACTS_RE, company_text, re.DOTALL, 1)

        if contacts_text is None:
            contacts_text = self.__search(ALT_CONTACTS_RE, company_text, re.DOTALL, 1)

        self.__process_contacts(company, contacts_text)

        self.companies.append(company)
    
    def __split_contacts(self, contact_text: str) -> list[str]:
        contact_list = self.__findall(CONTACTS_SPLIT_RE, contact_text, re.DOTALL)

        if len(contact_list):
            contact_list = [contact_text.split(contact_list[0])[0], *contact_list]

        return contact_list if len(contact_list) else [contact_text]

    def __process_contacts(self, company: Company, contact_text: str) -> None:
        if contact_text is None: return

        contact_list = self.__split_contacts(contact_text)
        
        [company.contacts.append(self.__extract_contact(text)) for text in contact_list]
    
    def __extract_contact(self, contact_text: str) -> Contact:
        name = self.__search(r"(.+)\n*", contact_text, group=1)

        title = self.__search(r"\n*([^\n]+?\:.+?)\n", contact_text, re.DOTALL, 1)

        email = self.__search(r"[\w\-\.*]+@\w+.\w{,5}", contact_text, re.DOTALL)

        telephone = self.__search(r"TEL.+?([+\(\)\d\s]+)", contact_text, re.DOTALL, 1)

        cell = self.__search(r"CELL.+?([+\(\)\d\s]+)", contact_text, re.DOTALL, 1)

        return Contact(name=name, title=title, email=email, tel=telephone, cell=cell)

    def __get_companies(self, index: int) -> None:
        text = self.reader.pages[index].extract_text(orientations=0)

        re_companies = self.__findall(COMPANIES_RE, f"{text[1:]}", re.DOTALL)

        companies = []

        [companies.extend(self.__split(f"{company.lstrip('.')}")) for company in re_companies]

        [self.__process_company(company) for company in companies]
        
        page_num = f"{index + 1}/{len(self.reader.pages)}"

        self.logger.info(f"Page: {page_num} || Total Companies: {len(self.companies)}")
    
    def __save(self) -> None:
        companies = [dataclasses.asdict(company) for company in self.companies]

        for company in companies:
            for key, value in company.items():
                if isinstance(value, list):
                    for contact in value:
                        for contact_key, contact_value in contact.items():
                            contact[contact_key] = self.__asciify(self.__strip(contact_value))
                        
                    continue

                company[key] = self.__asciify(self.__strip(value))
        
        with open("./data/data.json", "w") as file:
            json.dump(companies, file, indent=4)
        
        df_list = []

        for company in companies:
            df_company = {key:value for key, value in company.items() 
                          if key != "contacts" and key != "main_activity"}
            
            for index, contact in enumerate(company["contacts"]):
                df_company.update(
                    {f"contact_{index}_{k}": v for k, v in contact.items()})
            
            df_company["main_activity"] = company["main_activity"]

            df_list.append(df_company)
        
        df = pd.DataFrame(df_list)

        headings = ["company_name", 
                    "address", 
                    "company_tel", 
                    "website", 
                    "company_email",
                    *[header for header in df.columns.values if header.startswith("contact")],
                    "main_activity"]
        
        df[headings].to_excel("./data/data.xlsx", index=False)

    def run(self) -> None:
        [self.__get_companies(index) for index in range(len(self.reader.pages))]

        self.__save()

app = PDFExtractor()
app.run()