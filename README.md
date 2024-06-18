# easy-access-dashboard
A quickly hacked together python script to read in easy access data from the copyright tool -> generate .qmd files -> render into dashboards .

# How to use
Install the following items:

- python 3 (tested with 3.12)
- quarto (https://quarto.org/docs/get-started/)

If you want to use the automated script:
- uv (https://github.com/astral-sh/uv)
- single-file-cli (https://github.com/gildas-lormeau/single-file-cli) -- move the .exe to this dir

You'll need the following files in the dir:
- csv file export from the copyright tool, copyright_export.csv
- csv file with mapping of course names to faculty (this is not implemented yet!)
- csv file with manually added data per faculty: put in manual_sheets\<faculty_name>.csv

Then, to finalize the setup: open make_report.py and change the entries in FACULTYNAMES to the faculties you want to include. For each faculty 1 dashboard will be made. 

To create the dashboards you can either use the included ps1 powershell script, or do it manually.

## Powershell script
 - start Powershell
 - navigate to this dir
 - create a venv with the command: **uv venv**
 - then run make_dashboards.ps1
 - wait, done!

## Manually

Basics:
- create the .qmd files by running make_report.py
- create dashboards using quarto render

Look through make_report.py for all the different functions. 
