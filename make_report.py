import pandas as pd
import pickle
from rich import print
from typing import Any
from babel.numbers import format_currency
from babel.numbers import format_compact_currency
import os

'''
Script to process Easy Access data from surf copyrighttool and produce a report per faculty.
by Samuel Mok, s.mok@utwente.nl

Necessary data in order to run the script:
- csv file export from the copyright tool
- csv file with mapping of course names to faculty [READING THIS IN IS NOT IMPLEMENTED YET]
- csv file with manually added data + how it maps to the data from the copyright tool 
'''


# Change the entries in this list to the names of the faculty you want to include in the report/dashboard
FACULTYNAMES = ['BMS',
                'EEMCS',
                'TNW',
                'ET',
                'ITC'
                ]

class CopyRightData:

    def __init__(self, periods: list[str] = None, faculty: str = ''):
    
        self.mapping: dict = {}
        self.mapping = self.get_mapping()
        self.data: pd.DataFrame = pd.DataFrame()
        self.data_grouped: list[tuple[str, pd.DataFrame]]  = []
        self.periods: list[str] = periods if periods else []
        self.faculty: str = faculty
        self.faculty_data: pd.DataFrame = pd.DataFrame()
        self.stats: dict[str, Any] = {}
        self.all_long_excerpts: pd.DataFrame = pd.DataFrame()
        self.all_long_excerpts_grouped: list[tuple[str, pd.DataFrame]] = []

    def set_periods(self, periods: list[str]):
        self.periods = periods
    def get_periods(self) -> list[str]:
        return self.periods
    def set_faculty(self, faculty: str):
        self.faculty = faculty
    def get_faculty(self) -> str:
        return self.faculty

    def get_mapping(self) -> dict:
        '''
        Reads in mapping data from:
        - pickle if no file is provided
        - from parameter csv
        '''
        if not self.mapping:
            try:
                with open('faculties.pickle', 'rb') as handle:
                    self.mapping = pickle.load(handle)
            except Exception as e:
                print("no stored mappings found, run make_mapping() first. Trying now with default filename.")
                self.make_mapping()
                return self.mapping
        return self.mapping

    def make_mapping(self, filepath: str='faculty_course_mapping.csv') -> dict:
        '''
        makes mappings from csv file in filepath
        stores as pickle file + returns mapping
        '''
        try:
            with open(filepath, 'r') as f:
                mapping_raw = pd.read_csv(f)
        except Exception as e:
            print(f"error reading mapping file {filepath}")
            raise e
        
        # process data and store in self.mapping + pickle
        ...
        return self.mapping

    def get_data(self, filepath: str = 'copyright_export.csv') -> pd.DataFrame:
        try:
            self.data = pd.read_csv(filepath)
        except Exception as e:
            print(f"error reading data file {filepath}. Please check that the file exists and is in the correct format: \n     - {filepath} \n    - containing the necessary columns (see manual)")
            raise e
        copyright_data_raw = self.data[self.data['Period'].isin(self.periods)]
        copyright_data_raw = copyright_data_raw.assign(faculty='')
        if 'Google search file' in copyright_data_raw:
            copyright_data_raw.drop('Google search file', axis=1, inplace=True)
        copyright_data_raw = copyright_data_raw.astype({
                                                        'Material id':pd.Int64Dtype(),
                                                        'Period': pd.CategoricalDtype(),
                                                        'Department':pd.CategoricalDtype(),
                                                        'Course code':pd.StringDtype(),
                                                        'Course name':pd.StringDtype(),
                                                        'url':pd.StringDtype(),
                                                        'Filename':pd.StringDtype(),
                                                        'Title':pd.StringDtype(),
                                                        'Owner':pd.StringDtype(),
                                                        'Filetype':pd.CategoricalDtype(),
                                                        'Classification':pd.CategoricalDtype(),
                                                        'Type':pd.CategoricalDtype(),
                                                        'ML Prediction':pd.CategoricalDtype(),
                                                        'Manual classification':pd.CategoricalDtype(),
                                                        'Manual identifier':pd.StringDtype(),
                                                        'Scope':pd.StringDtype(),
                                                        'Remarks':pd.StringDtype(),
                                                        'Auditor':pd.StringDtype(),
                                                        'Last change':pd.StringDtype(),
                                                        'Status':pd.CategoricalDtype(),
                                                        'DOI':pd.StringDtype(),
                                                        'Author':pd.StringDtype(),
                                                        'Publisher':pd.StringDtype(),
                                                        'Pages * Students':pd.Int64Dtype(),
                                                        })
        self.get_mapping()
        copyright_data_raw = copyright_data_raw.assign(faculty=lambda x: x['Course name'].map(self.mapping))
        copyright_data_raw['faculty'] = copyright_data_raw['faculty'].astype('category')
        copyright_data_raw['Expected fine'] = copyright_data_raw[copyright_data_raw['Classification'] == 'lange overname']['Pages * Students'].mul(0.3)
        self.data_grouped = copyright_data_raw.groupby(by=['faculty'], observed=False)
        if self.faculty in FACULTYNAMES:
            for name, details in self.data_grouped:
                if name[0] == self.faculty:
                    self.faculty_data = details
                    self.add_student_sheet_data()

        self.calculate_stats()
        return self.format_costs()

    def add_student_sheet_data(self) -> None:
        '''
        load in manual data sheet for the faculty and add to faculty_data
        match items in self.faculty_data with items in the manual sheet
        '''
        if not self.faculty:
            return None
        if self.faculty_data.empty:
            self.get_data()
            if self.faculty_data.empty:
                raise Exception(f'No copyright tool data found for {self.faculty} -- cannot add manual sheet data.')

        file_path = os.path.join('manual_sheets', f'{self.faculty}.csv')
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
        except Exception as e:
            print(f"error reading student data file {file_path}. Please check that the file exists and is in the correct format: \n     - manual_sheets/{self.faculty}.csv \n    - containing the necessary columns (see manual)")
            raise e
        df['url_id_x'] = df['url_id_x'].astype('str')
        prefix_to_remove = 'https://utwente.instructure.com/files/'
        self.faculty_data['id_cc'] = self.faculty_data['url'].str.replace(prefix_to_remove, '', regex=False).str.replace('?', '', regex=False)
        self.faculty_data.sort_values(by=['id_cc'], inplace=True)
        self.faculty_data = pd.merge(self.faculty_data, df.sort_values(by=['url_id_x']),  how="left", left_on="id_cc", right_on="url_id_x").dropna(axis='columns',how='all')
        column_names = {
            'Classification_x': 'Classification',
            'Manual classification_y': 'Manual classification',
            'Owner_x': 'Owner',
            'Course code_x': 'Course code',
            'Period_x': 'Period',
            'Type_x': 'Type',
            'Manual identifier_x': 'Manual identifier',
            'Scope_x': 'Scope',
            'Remarks_x': 'Remarks',
            'Auditor_x': 'Auditor',
            'Last change_x': 'Last change',
            'ISBN_x': 'ISBN',
            'DOI_x': 'DOI',
            'In collection_x': 'In collection',
            'pagecount_x': 'pagecount',
            'wordcount_x': 'wordcount',
            'picturecount_x': 'picturecount',
            'Reliability_x': 'Reliability',
            'Pages * Students_x': 'Pages * Students',
            '#students_registered_x': '#students registered',
            'Status_y': 'Status',
            'Filetype_x':'Filetype',
            'Status_x': 'Status_recent',
            }
        self.faculty_data.rename(columns=column_names, inplace=True)
        droplist = [
            'id_cc',
            'Unnamed: 0',
            'Classification_y',
            'Reliability_y',
            'Period_y',
            'Course code_y',
            'url_id_x',
            'id_y',
            'Title_x',
            'Owner_y',
            'Filetype_y',
            'Type_y',
            'Scope_y',
            'Remarks_y',
            'Auditor_y',
            'Last change_y',
            'updated_at',
            'Status2',
            'ISBN_y',
            'DOI_y',
            'In collection_y',
            'pagecount_y',
            'wordcount_y',
            'picturecount_y',
            'Pages * Students_y',
            '#students_registered_y',
            'Publisher_x',
            'Manual identifier_y',
            'Manual classification_x',

        ]
        try:
            self.faculty_data.drop(droplist, axis=1, inplace=True)
        except Exception as e:
            #print('cannot drop columns for faculty', self.faculty)
            ...
        try:
            self.faculty_data.drop('Classification ->', axis=1, inplace=True)
        except Exception as e:
            ...
        if 'Manual classification' not in self.faculty_data.columns:
            if 'Manual classification_y' in self.faculty_data.columns:
                self.faculty_data['Manual classification'] = self.faculty_data['Manual classification_y']
                self.faculty_data.drop('Manual classification_y', axis=1, inplace=True)
            elif 'Manual classification_x' in self.faculty_data.columns:
                self.faculty_data['Manual classification'] = self.faculty_data['Manual classification_x']
                self.faculty_data.drop('Manual classification_x', axis=1, inplace=True)
            else:
                self.faculty_data['Manual classification'] = '-'
        
    def get_stats(self) -> dict[str, Any]:

        if not self.stats:
            self.calculate_stats()
        return self.stats

    def calculate_stats(self, department:str|None = None) -> None:
        if not self.faculty_data.empty:
            if department:
                calcdata = self.faculty_data[self.faculty_data['Department'] == department]
            else:
                calcdata = self.faculty_data
            for name, count in calcdata['Classification'].value_counts().items():
                self.stats[name] = count
            self.stats['total_costs'] = calcdata['Expected fine'].sum()
            self.stats['lange overname manual'] = self.get_long_excerpts(all=False, format=False, department=department).shape[0]
            self.stats['total_costs_manual']= self.get_long_excerpts(all=False, format=False, department=department)['Expected fine'].sum()
            self.stats['total_items'] = calcdata.shape[0]
        else:
            for name, details in self.data_grouped:
                self.stats[name[0]] = {}
                for key, value in details['Classification'].value_counts().items():
                    self.stats[name[0]][key] = value
                self.stats[name[0]]['total_costs'] = details['Expected fine'].sum()

    def format_costs(self):
        if not self.faculty_data.empty:
            if not self.stats:
                self.stats['total_costs'] = self.faculty_data['Expected fine'].sum()
            self.faculty_data['Expected fines'] = self.faculty_data['Expected fine'].dropna().apply(lambda x: format_currency(x, currency="EUR", locale="nl_NL")).astype('str')
            return self.faculty_data
        else:
            for name, details in self.data_grouped:
                if not self.stats[name[0]]:
                    self.stats[name[0]]['total_costs'] = details['Expected fine'].sum()
                self.data_grouped[name].loc[:, 'Expected fines'] = details['Expected fine'].apply(lambda x: format_currency(x, currency="EUR", locale="nl_NL")).astype('str')
            return self.data_grouped

    def get_long_excerpts(self, all: bool = True, format:bool = True, department: str|None = None) -> pd.DataFrame | list[tuple[str, pd.DataFrame]]:
        '''
        returns a dataframe with all long excerpts or only thos that aren't overridden by manual classification
        '''
        if not self.faculty_data.empty:
            self.all_long_excerpts = self.faculty_data[self.faculty_data['Classification'] == 'lange overname']
            if 'Own_work' in self.faculty_data.columns:
                self.all_long_excerpts = self.all_long_excerpts[~self.all_long_excerpts['Own_work'].isin(['Yes', 'yes'])]
            if 'Free_for_use' in self.faculty_data.columns:
                self.all_long_excerpts = self.all_long_excerpts[~self.all_long_excerpts['Free_for_use'].isin(['Yes', 'yes'])]
            if 'Status_recent' in self.faculty_data.columns:
                self.all_long_excerpts = self.all_long_excerpts[~self.all_long_excerpts['Status_recent'].isin(['Deleted', 'deleted'])]
            if 'ML Prediction' in self.faculty_data.columns:
                self.all_long_excerpts = self.all_long_excerpts[~self.all_long_excerpts['ML Prediction'].isin(['eigen materiaal - powerpoint'])]
            cols = self.all_long_excerpts.columns.tolist()
            if 'Status' in cols:
                cols.insert(1,cols.pop(cols.index('Status')))
            if 'Suggested action' in cols:
                cols.insert(2,cols.pop(cols.index('Suggested action')))
            if 'Extra notes' in cols:
                cols.insert(3,cols.pop(cols.index('Extra notes')))
            if 'Own_work' in cols:
                cols.insert(4,cols.pop(cols.index('Own_work')))
            if 'Free_for_use' in cols:
                cols.insert(5,cols.pop(cols.index('Free_for_use')))
            self.all_long_excerpts = self.all_long_excerpts[cols]

            if all:
                return self.all_long_excerpts
            else:
                
                self.all_long_excerpts = self.all_long_excerpts[~self.all_long_excerpts['Manual classification'].isin(['eigen materiaal - powerpoint', 'open access', 'eigen materiaal - overig'])]
                if format:
                    return self.format_long_excerpt(department=department)
                else:
                    if department:
                        return self.all_long_excerpts[self.all_long_excerpts['Department'] == department]
                    else:
                        return self.all_long_excerpts
        else:
            for name, details in self.data_grouped:
                tmp = details[details['Classification'] == 'lange overname']
                tmp = tmp[details['Own_work'] != 'Yes']
                tmp = tmp[details['Free_for_use'] != 'Yes']
                if all:
                    self.all_long_excerpts_grouped.append((name[0], tmp))
                else:
                    self.all_long_excerpts_grouped.append((name[0], tmp[~tmp['Manual classification'].isin(['eigen materiaal - powerpoint', 'open access', 'eigen materiaal - overig'])]))
            return self.all_long_excerpts_grouped

    def format_long_excerpt(self, department:str|None = None) -> pd.DataFrame:
        return_data = self.all_long_excerpts
        return_data['Title'] = return_data['Title'].fillna('')
        return_data['Owner'] = return_data['Owner'].fillna('')
        return_data.drop(['url', 'Material id', 'Type', 'Auditor',  'Scope', 'Manual identifier', 'Pages * Students'], axis=1, inplace=True)
        cols = return_data.columns.tolist()
        cols = cols[-1:] + cols[:-1]
        return_data = return_data[cols]
        if not department:
            return_data.sort_values('Department')
        else:
            return_data = return_data[return_data['Department'] == department]

        return return_data

    def get_programme_list(self) -> list[str]:
        '''
        returns a list of all programmes in the data
        '''
        if not self.faculty_data.empty:
            programmes = self.faculty_data['Department'].unique().tolist()
            print(programmes)
            return programmes
        

def create_qmds(periods: list[str] = None) -> None:
    '''
    creates a qmd file for each faculty
    afterwards, run quarto render dashboard_<faculty>.qmd to create each dashboard
    use single-file-cli (https://github.com/gildas-lormeau/single-file-cli) to combine the js/css/images for the dashboard into the .html file itself. 

    a powershell script is provided in the repo to do this automatically - make_dashboards.ps1. Make sure to install quarto, single-file-cli, and uv first, and activate the uv venv before running the script.
    '''
    if not periods:
        periods = ['2022', '2022-2A', '2022-2B', '2022-JAAR', '2022-SEM 2']
    for faculty in FACULTYNAMES:
        try:
            print(faculty)
            dataclass = CopyRightData(periods=periods, faculty=faculty)
            data: pd.DataFrame = dataclass.get_data()
            stats: dict = dataclass.get_stats()
            
            total_costs_manual = format_compact_currency(stats['total_costs_manual'], currency="EUR", locale="nl_NL").replace(u'\xa0','')
        except Exception as e:
            print(f"error in {faculty}: {e}")
            continue
        

        totalstring = f'''---
title: "Dashboard Easy Access"
author: "cip@utwente.nl"
format:
    dashboard:
        logo: easy_access_logo_beach.svg
        html-table-processing: none
        theme:
            - litera
            - custom.scss
---
```{{python}}
#| echo: false
#| output: false
import pandas as pd
from itables import show, init_notebook_mode
from make_report import CopyRightData
from babel.numbers import format_compact_currency
from IPython.display import display, Markdown
init = init_notebook_mode(all_interactive=True, connected=True)
faculty = '{faculty}'
periods = ['2022', '2022-2A', '2022-2B', '2022-JAAR', '2022-SEM 2']
dataclass = CopyRightData(periods=periods, faculty=faculty)
data = dataclass.get_data()
stats: dict = dataclass.get_stats()
total_costs_manual = format_compact_currency(stats['total_costs_manual'], currency="EUR", locale="nl_NL").replace(u'\xa0','')
```
# Overview {faculty}
## Row
```{{python}}
#| content: valuebox
#| title: "Possible fine"
dict(
icon = "currency-exchange",
color = "danger",
value = '{total_costs_manual}'

)
```
```{{python}}
#| content: valuebox
#| title: "# of scanned documents"
dict(
icon = "stack-overflow",
color = "info",
value = {str(stats['total_items'])}
)
```
```{{python}}
#| content: valuebox
#| title: "# of infractions"
dict(
icon = "exclamation-square-fill",
color = "warning",
value = {str(stats['lange overname manual'])}
)
```
## Row
```{{python}}
#| title: All items in need of action
show(dataclass.get_long_excerpts(all=False), buttons = ['copy', 'excel', 'pdf'], showIndex=False)
```
```{{python}}
#| title: All items marked as 'lange overname' by Copyright Tool
show(dataclass.get_long_excerpts(all=True), buttons = ['copy', 'excel', 'pdf'], showIndex=False)
```
'''
        dept_data = {}
        programme_list = dataclass.get_programme_list()
        for dept in programme_list:
            dataclass.calculate_stats(department=dept)
            dept_data[dept] = {}
            dept_data[dept]['stats'] = dataclass.get_stats()
            dept_data[dept]['total_costs'] = format_compact_currency(dept_data[dept]['stats']['total_costs'], currency="EUR", locale="nl_NL").replace(u'\xa0','')
            total_costs_manual = format_compact_currency(dept_data[dept]['stats']['total_costs_manual'], currency="EUR", locale="nl_NL").replace(u'\xa0','')
            totalstring += f'''
# {dept.split(':')[0]}
## Row
```{{python}}
#| content: valuebox
#| title: "Possible fine"
dict(
icon = "currency-exchange",
color = "danger",
value = '{total_costs_manual.replace(u'\0xAC', '€').replace(u'\FFFD', '' )}'

)
```
```{{python}}
#| content: valuebox
#| title: "# of scanned documents"
dict(
icon = "stack-overflow",
color = "info",
value = {str(dept_data[dept]['stats']['total_items'])}
)
```
```{{python}}
#| content: valuebox
#| title: "# of infractions"
dict(
icon = "exclamation-square-fill",
color = "warning",
value = {str(dept_data[dept]['stats']['lange overname manual'])}
)
```
## Row
```{{python}}
show(dataclass.get_long_excerpts(all=False, department='{dept}'), buttons = ['copy', 'excel', 'pdf'], showIndex=False)
```
'''

        with open(f'dashboard_{faculty}.qmd', 'w', encoding='utf-8') as f:
            f.write(totalstring)
    

def test_one(faculty: str, periods: list[str]):
    dataclass = CopyRightData(periods=periods, faculty=faculty)
    data: pd.DataFrame = dataclass.get_data()
    stats: dict = dataclass.get_stats()

    print(stats)
    print(data.info(verbose=True, show_counts=True))
    short_data = data[data['Classification'] == 'lange overname'].sort_values('Course name')
    print(short_data.info(verbose=True, show_counts=True))
    print(short_data['Expected fine'].head(50))
    print(stats)

if __name__ == '__main__':
    # test getting the data for a single faculty for [periods]
    #faculty = 'TNW'
    #periods=['2022', '2022-2A', '2022-2B', '2022-JAAR', '2022-SEM 2']
    #test_one(faculty, periods)

    # create qmd dashboard files for each faculty in FACULTYNAMES
    create_qmds()