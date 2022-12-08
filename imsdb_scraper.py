from urllib.parse import urljoin
import os
import logging
import csv
import sys
import requests
from bs4 import BeautifulSoup



logging.basicConfig(level=logging.DEBUG)

DOMAIN = "https://imsdb.com"


def main(filename):
    all_scripts_path = "/all-scripts.html"
    imsdb_soup = get_soup(urljoin(DOMAIN, all_scripts_path))
    movie_list_container = imsdb_soup.find_all('td', {'valign': 'top'})[2]
    for paragraph in movie_list_container.find_all('p'):
        # Get title without substring ' Script' at the end
        title = paragraph.a['title'][0:-7]
        logging.info('Pasing %s', title)
        # Compose URL and handle escape characters
        movie_url = urljoin(DOMAIN, paragraph.a['href'].
                            replace(' ', '%20').
                            replace('?', '%3F')
                            )
        movie_soup = get_soup(movie_url)
        logging.info('Going to %s', movie_url)
        movie_data = parse_movie(movie_soup, title)
        # Append metadata to list only if full parsing has succeeded
        if movie_data:
            write_csv(movie_data, filename)
    logging.info('No more movies to parse')


def get_soup(url):
    source = requests.get(url)
    soup = BeautifulSoup(source.text, 'html.parser')
    return soup


def parse_movie(movie_soup, movie_title):
    logging.info('Starting parsing %s', movie_title)
    table_details = movie_soup.find('table', {'class': 'script-details'})
    movie_meta = {}
    movie_meta['title'] = movie_title
    # Get all genres (can be more than one)
    movie_meta['genre'] = [a.string for a in table_details.find_all('a')
                           if a['href'].startswith('/genre')]
    # Get all writers (can be more than one)
    movie_meta['writers'] = [a.string for a in table_details.find_all('a')
                             if a['href'].startswith('/writer')]
    # Get URL at the end
    try:
        last_url = table_details.find_all('a')[-1]
    except IndexError:
        logging.debug('No URL found in %s', movie_title)
        return None
    # Check if URl is actually the script
    if not last_url.text.startswith('Read'):
        logging.debug('Cannot find script in %s', movie_title)
        return None
    script_path = last_url['href']
    movie_meta['url'] = urljoin(DOMAIN, script_path)
    # Proceed with script parsing if script is in HTML format (there are some PDFs)
    if script_path.endswith('html'):
        script_soup = get_soup(movie_meta['url'])
        if get_script_txt(script_soup):
            movie_meta['script'] = get_script_txt(script_soup)
        else:
            logging.debug('%s has no script', movie_title)
            return None
    else:
        logging.debug('Cannot parse %s', movie_title)
        logging.debug('Script is not in HTML format')
        return None
    logging.info('Parsing successfully completed')
    return movie_meta


def get_script_txt(script_soup):
    script = script_soup.find('td', {'class': 'scrtext'})
    elements2remove = ['table', 'div', 'tr']
    for element2remove in elements2remove:
        [element_found.decompose()
         for element_found in script.find_all(element2remove)]
    # Use square bracket to mark bold text
    for bold in script.find_all('b'):
        bold.string = ''.join(f'[{bold.string}]'
                           .split()).replace('[]', '') + '\n'
    # Return None if text is nothing but space
    if not script.get_text().isspace():
        return script.get_text()
    return None


def write_csv(data, filename):
    # Check if file already exists to write column names only once
    if os.path.exists(filename):
        write_column_names = False
        logging.info('Creating CSV file')
    else:
        write_column_names = True
    # Write or keep writing CSV file
    with open(filename, 'a+', newline='', encoding='UTF-8') as output_file:
        writer = csv.writer(output_file)
        if write_column_names:
            logging.info('Writing column names')
            writer.writerow(data.keys())
        logging.info('Adding books')
        writer.writerow(data.values())


if __name__ == '__main__':
    main(sys.argv[1])
