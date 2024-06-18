# Powershell script to create Easy Access dashboards for each faculty
# requirements:
# - python 3.10 (or something, made with 3.12)
# - quarto (https://quarto.org/docs/get-started/)
# - uv (https://github.com/astral-sh/uv)
# - single-file-cli (https://github.com/gildas-lormeau/single-file-cli)


# get current working directory
$cwd = Get-Location

# activate venv and install requirements
.\.venv\Scripts\Activate.ps1
uv pip install -Ur .\requirements.txt

# 1. run python files to generate the QMD files
# a) NOT IMPLEMENTED YET: retrieve list of faculties from user/file/whatever
$facultylist = @('BMS', 'EEMCS', 'TNW', 'ET', 'ITC')
python .\make_report.py

# 2. run quarto to render the QMD files to dashboards, and use single-file to inline the css/js/images/etc

foreach ($faculty in $facultylist) {
    quarto render .\dashboard_$faculty.qmd
    .\single-file $cwd\dashboard_$faculty.html $cwd\easy_access_$faculty.html
    #Remove-Item $cwd\dashboard_$faculty.html
    #Remove-Item $cwd\dashboard_$faculty.qmd
    #Remove-Item -recurse $cwd\dashboard_$faculty_files\*
}


Write-Host "Done. The dashboards can be found in this folder ($cwd), named easy_access_<faculty>.html."

