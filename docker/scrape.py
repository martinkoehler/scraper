#!/usr/bin/env python3
# -*- coding: utf-8 -*-
##
## This file is part of Scraper
## Copyright (C) 2021 mkoehler
##
## Scraper is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## Scraper is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Invenio; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
"""
This module can be used to get data from the WoS Website
"""

# Variable naming conventions: we use Uppercase for function names:
# pylint: disable=C0103

import argparse
import logging
import io
#from urllib3.exceptions import MaxRetryError
#from shutil import rmtree
from contextlib import contextmanager
import seleniumwire.undetected_chromedriver as uc
import pandas as pd
from seleniumwire.utils import decode
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
# See http://www.obeythetestinggoat.com/how-to-get-selenium-to-wait-for-page-load-after-a-click.html
#from contextlib import contextmanager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import staleness_of
from selenium.common.exceptions import NoSuchElementException, \
                                       TimeoutException, \
                                       WebDriverException, \
                                       InvalidSessionIdException
logging.basicConfig()
logger = logging.getLogger(__name__)

class Scraper:
    """
    This program fetches WoS records for a list of DOIs
    The result is one excel file with the FULL RECORD of all DOIs and the
    DOIs that cite the Publications from the list.
    The first column contains the DOI, where the records belong to.
    You need a WoS license to access the website
    """
    def __init__(self):
        self.startpage = "https://www.webofscience.com/wos/woscc/advanced-search"
        self.driver = self._create_driver()
        self._start_session()

    @contextmanager
    def wait_for_page_load(self, timeout=10):
        """
        Implement a contextmanager that waits for a page change
        """
        logger.debug(f"Waiting for page to load at {self.driver.current_url}.")
        old_page = self.driver.find_element(By.TAG_NAME, 'html')
        logger.debug(f"At {old_page}")
        yield
        logger.debug("After yield")
        WebDriverWait(self.driver, timeout).until(EC.staleness_of(old_page))
        logger.debug("wait_for_page_load finished at {self.driver.current_url}")


    def _wait_and_click(self, by, text, timeout=10):
        """
        Make sure the element we want to click is there
        """
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, text))
            )
        except TimeoutException:
            logger.fatal(f'Element {text} not found')
            return False
        element.click()
        return True

    def _create_driver(self):
        """
        Create a webdriver
        """
        logger.debug("Creating driver")
        chrome_options = uc.ChromeOptions()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--no-first-run')
        #options.binary_location = "/usr/bin/fater-chrome"
        #driver = uc.Chrome(options=chrome_options, seleniumwire_options={})
        driver = uc.Chrome(options=chrome_options)
        logger.debug("Driver created")
        return driver


    def _start_session(self):
        """
        Start a WoS session and reject cookies
        """
        logger.debug("Starting session")
        #  Goto Advanced search
        self.driver.get(self.startpage)
        # Click reject cookies
        self._wait_and_click(By.ID,"onetrust-reject-all-handler")
        logger.debug("Session started")
        return self.driver

    def _search_doi(self, doi):
        """
        Search for a single DOI
        return result page
        """
        logger.debug(f"Searching for doi {doi} ...")
        if self.driver.current_url != self.startpage:
            self.driver.get(self.startpage)
        doi_query = f"DO=({doi})"
        # Fill the input box via JS, since send_keys("/") does not work in WoS
        input_id="advancedSearchInputArea"
        js = f'document.getElementById("{input_id}").value="{doi_query}"'
        try:
            search_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, input_id))
            )
        except TimeoutException:
            logger.fatal(f'Element {input_id} not found')
            return False
        logger.debug(f'{input_id} Element found. Setting value with js ...')
        self.driver.execute_script(js)
        logger.debug("...done")
        # Find input Box
        # Enter query and search
        logger.debug(f"Do the search from {self.driver.current_url}")
        #with wait_for_page_load(driver):
        logger.debug("Sending keys")
        search_input.send_keys(" " + Keys.ENTER)
        logger.debug("Keys sent")
        try:
            WebDriverWait(self.driver, 10).until(EC.staleness_of(search_input))
        except TimeoutException:
            logger.fatal(f'Element {search_input} not stale')
            return False
        logger.debug(f"New page: {self.driver.current_url}")
        logger.debug(f"...done (search_doi)")
        return self.driver

    def _export_records(self):
        """
        Exports all WoS records from a result page
        """
        logger.debug("Exporting records ...")
        res =  self._wait_and_click(By.XPATH,
          '//span[@class="mat-button-wrapper" ' + \
          ' and contains(text(),"Export")]') \
        and \
        self._wait_and_click(By.XPATH,
            "//button[@id='exportToExcelButton']") \
        and \
        self._wait_and_click(By.XPATH,
            "//input[@class='mat-radio-input' "+ \
            "and @value='fromRange']/../..") \
        and \
        self._wait_and_click(By.XPATH,
            "//button[@aria-label=' Author, Title, Source']") \
        and \
        self._wait_and_click(By.XPATH,
            '//div[@title="Full Record"]') \
        and \
        self._wait_and_click(By.XPATH,
            '//span[contains(text(),"Export")]')
        if not res: # something wrong
            logger.error("Export to excel did not work")
            return False
        try:
            response = self.driver.wait_for_request('export/saveToFile',
                                               timeout=30).response
        except TimeoutException:
            logger.error("Excel Download failed")
            return False
        res = decode(response.body, response.headers.get('Content-Encoding',
                                                          'identity'))
        df = pd.read_excel(pd.ExcelFile(io.BytesIO(res)))
        del self.driver.requests # Make sure the next response is "new" again
        logger.debug(f'{len(df)} exported')
        logger.debug("...done (export_record)")
        return df

    def get_data(self, doi):
        """
        Retrieve a doi and all records citing this doi
        Return a dataframe with the full WOS of all records, where the citing
        records have the doi on their last column, called doi
        """
        logger.debug("Getting data ...")
        if self._search_doi(doi) is False:
            return False
        df1 = pd.DataFrame()
        df2 = pd.DataFrame()
        # Export record of this doi
        # response is the excel file
        df1 = self._export_records()
        if isinstance(df1, pd.DataFrame):
            df1["citing_doi"] = "" # No entry here
        # Get citations
        try:
            logger.debug("Try to get citations")
            url = self.driver.find_element(By.XPATH,
               "//div[@class='citations ng-star-inserted']"+\
               "/div[@class='font-size-14 " + \
               "data-box-text' and contains(text(),"+ \
               " 'Citation')]/../a").get_attribute("href")
            self.driver.get(url)
            logger.debug("Citation link found")
            df2 = self._export_records()
            if isinstance(df2, pd.DataFrame):
                # Insert doi of original here
                df2["citing_doi"] = [doi] * (len(df2))
        except NoSuchElementException:
            logger.info(f'No citations found for {doi}')
        logger.debug("...done (get_data)")
        return pd.concat([df1,df2])

#======================================================================
def main(infile):
    """
    Read csv with DOIs and return excel object
    """
    logger.info("Entering main")
    dois=pd.read_csv(infile, header=None, names=["doi"]) # No header in file
    logger.info(f'{len(dois)} DOI\'s found')
    logger.info("Initializing ...")
    scapper = Scraper()
    logger.info("... done")
    finaldf = pd.DataFrame() # Empty Dataframe
    # loop here
    for index,doi in dois.itertuples(index=True, name="doi"):
        i = 0
        while True:
            try:
                logger.info(f"Fetching data for doi: {doi}")
                df = scapper.get_data(doi)
                if isinstance(df, pd.DataFrame):
                    logger.info(f'Got {len(df)} record(s)')
                    # concat all results
                    finaldf = pd.concat([finaldf,df])
                else:
                    logger.warning(f'Got no data for {doi}')
            except BaseException as err:
                logger.error(f"Unexpected {err=}, {type(err)=}")
                i +=1
                if i > 3: 
                    break
                continue
            break # Only loop once if everything is ok
    return finaldf

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', default=0, action='count')
    parser.add_argument('--outfile', '-O', default="data/final.xlsx")
    parser.add_argument('--infile', '-i', default="data/dois.csv")
    args = parser.parse_args()

    logger.info('Scraping WoS')

    if args.verbose == 0:
        # Default
        log_level = logging.WARNING
    elif args.verbose == 1:
        log_level = logging.INFO
    elif args.verbose == 2:
        log_level = logging.DEBUG
    else:
        log_level = logging.ERROR
    logger.setLevel(log_level)
    #logger.debug(f'Log level = {log_level}')
    result = main(args.infile)
    logger.info(f'Creating {args.outfile} with '+ \
                f'{len(result)}' + \
                ' record(s)')
    result.to_excel(args.outfile)
