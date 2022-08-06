<meta http-equiv='Content-Type' content='text/html; charset=utf-8' />

<!-- markdownlint-disable MD003 MD033 MD034 -->

Scraper
=======
A docker container to get data from the WebOfScience Web page.
You need a valid subscription to get data

## Prerequisites: 
You need Docker (https://www.docker.com/) docker-compose and `make`

## Dockerfile
For windows the easiest way probably is to use the 
Windows Linux Subsystem (version 2) and Docker for windows.


To run the docker image clone this repositorium and issue 
`make`
This might take some time for the first run and results in a shell in the
container.

The output data is directly accessible from the host under `vol/data` 
(e.g. vol/data/final.xlsx`)

## Preparing the input file
Prepare a file with all the DOIs you want to use. One DOI per line.
The default filename is `dois.csv` located under `vol/data/`

The scraper will fetch the full record for all these DOIs in excel and include
full records of all documents that cite the DOI. To allow further post
processing, a column with the DOI that these citing records belong to is added
to the excel sheet. The default for the output file is `final.xlsx`, which will
be stored at `/vol/data/final.xlsx`

## Scraping
Start the container running `make` and run `xvfb-run ./scrap.py -v` 
from the shell within the container.
The resulting excel file will be available at the host under
`vol/data/final.xlsx`

# Note
If you are using afs: The `vol` directory must be accessible (rw) without a
token, e.g. must reside on a local drive.

## Hint
Create a `vol` directory locally and link this to `vol` in this directory.
You can also create `vol/data/dois.csv` before running `make`.

<!-- vim: spell spelllang=en_gb bomb
-->

