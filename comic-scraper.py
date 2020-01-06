import requests, os, re, logging, shelve, threading, math
from bs4 import BeautifulSoup
from os import path
from dataclasses import dataclass
from abc import ABC
from itertools import zip_longest

def grouper(n, iterable, padvalue=None):
    "grouper(3, 'abcdefg', 'x') --> ('a','b','c'), ('d','e','f'), ('g','x','x')"
    return zip_longest(*[iter(iterable)]*n, fillvalue=padvalue)

class ComicScraper(ABC):
	"""
	Extensible comic scraper that downloads images into folder with web comic's name
	with format [six zero padded page number]__[page title].[image extension]
	"""

	def __init__(self):
		self.logger = logging.getLogger(__name__)

		self.num_threads = 20
		self.shelve_name = 'comic_scraper'

	def get_base_url(self):
		""" e.g. xkcd.com """
		pass

	def get_next_comic_url(self, page_soup, page_number):
		""" return the url of the page following the given page """
		pass

	def get_image_url(self, page_soup, page_number):
		""" return the image url on the given page """
		pass

	def get_page_name(self, page_soup, page_number):
		""" return the string that you want to appear in the image file name for this page """
		pass

	def guess_urls_from_page_number(self, page_number):
		""" return list of possible urls for the given page number, each will be tried e.g. ['xkcd.com/2249'] """
		pass

	def is_last_page(self, page):
		""" return true if given ComicPage is the last page -- used to figure out when to stop when no stop page is given """
		return page.next_page_url is None

	def reset(self):
		"""
		clears the shelved comic pages
		"""
		db = shelve.open(self.shelve_name)
		if db.get(self.get_base_url()) is not None:
			db[self.get_base_url()] = Comic()

	def scrape(self, start=1, stop=None, comic=None):
		"""
		downloads images from the given page range (ints) into folder same as base url

		Parameters
		start (int): starting page number
		stop (int): download this page and stop
		comic (Comic): comic prepopulated with page info
		"""
		if stop is None:
			self.logger.info(f'starting scrape of ALL pages')
		else:
			self.logger.info(f'starting scrape of {stop - start + 1}')

		if comic is None:
			self.logger.debug('attempting to recover comic info from shelve')
			comic = shelve.open(self.shelve_name).get(self.get_base_url())

		if comic is None:
			self.logger.debug('creating new comic')
			comic = Comic()

		# scrape image urls and comic urls
		current_page_number = start - 1
		while stop is None or current_page_number < stop:
			current_page_number += 1
			page = comic.getpage(current_page_number)
			if page is None or page.image_url is None:
				urls = [self._get_page_url(current_page_number, comic)]
				if not isinstance(urls, list):
					urls = [urls]
				if urls[0] is None:
					urls = self.guess_urls_from_page_number(current_page_number)
					self.logger.debug(f'guessing urls {urls}')

				curr_url = None
				for url in urls:
					curr_url = url
					soup = self._download_page(url)
				
				if soup is None:
					self.logger.warning(f'could not generate soup for page {current_page_number}')
					break

				page = ComicPage(current_page_number, curr_url)
				page.next_page_url = self.get_next_comic_url(soup, current_page_number)
				page.image_url = self.get_image_url(soup, current_page_number)
				page.name = self.get_page_name(soup, current_page_number)
				if page.next_page_url is None:
					self.logger.warning(f'could not find next page url in page {current_page_number}')
				if stop is None and self.is_last_page(page) :
					self.logger.debug(f'found last page {current_page_number}')
					break

				comic.addpage(page)

		self.logger.debug('comic page download complete - downloading images')

		# download images up to last successfully downloaded comic
		os.makedirs(self.get_base_url(), exist_ok=True)
		self._start_download_image_threads(range(start, current_page_number + 1), comic)

		self.logger.debug('download complete - updating shelve')
		shelve.open(self.shelve_name)[self.get_base_url()] = comic

	def _get_image_extension(self, url):
		if url is None:
			return None
		match = re.search('(\.(gif|jpg|jpeg|tiff|png))$', url, re.IGNORECASE)
		if match is None:
			return None
		return match.group(1)

	def _get_image_filepath(self, page):
		self.logger.debug(f'image url is {page.image_url}')
		extension = self._get_image_extension(page.image_url)
		self.logger.debug(f'page number {page.number}')
		self.logger.debug(f'page name {page.name}')
		self.logger.debug(f'ext {extension}')
		if extension is None:
			return None
		return self.get_base_url() + path.sep + str(page.number).zfill(6) + '__' + page.name + extension

	def _download_page(self, url):
		""" download comic at given page and return resulting soup - return None on error """
		self.logger.debug(f'downloading comic at {url}')
		
		if re.search('^https?:\/\/', url) is None:
			url = f'http://{url}'

		# download page
		resp = requests.get(url)
		if not resp.ok:
			self.logger.warning(f'invalid response {resp.status_code}')
			return None

		# return the soup
		self.logger.debug(f'comic successfully downloaded')
		return BeautifulSoup(resp.content, 'lxml')

	def _download_image(self, page_number, comic):
		self.logger.debug(f'downloading image for page {page_number}')
		if page_number is None:
			return

		page = comic.getpage(page_number)
		if page is None:
			self.logger.warning(f'could not find page {page_number} information')
			return

		image_path = self._get_image_filepath(page)
		if image_path is None:
			self.logger.warning(f'could not discover file path for page {page_number}')
		elif path.exists(image_path):
			self.logger.debug(f'page {page_number} image already downloaded')
		elif page.image_url is None:
			self.logger.warning(f'page {page_number} has no image url yet')
		else:
			self.logger.debug(f'downloading {page.image_url}')
			if re.search('^https?:\/\/', page.image_url) is None:
				if re.search('^\/\/', page.image_url) is None:
					page.image_url = f'http://:{page.image_url}'
				else:
					page.image_url = f'http:{page.image_url}'

			resp = requests.get(page.image_url)
			if resp.ok:
				with open(image_path, 'wb') as f:
					self.logger.debug(f'saving to {image_path}')
					f.write(resp.content)
			else:
				logger.warning(f'invalid response {resp.status_code}')

	def _download_images(self, page_numbers, comic):
		self.logger.debug(f'downloading {len(page_numbers)} images')
		for page_number in page_numbers:
			self._download_image(page_number, comic)


	def _start_download_image_threads(self, all_page_numbers, comic):
		# todo - right number of threads?
		self.logger.info(f'starting threads to download {len(all_page_numbers)} pages')
		threads = []
		max_elements_per_chunk = math.ceil(len(all_page_numbers) / self.num_threads)
		self.logger.info(f'max elements per threads {max_elements_per_chunk} pages')
		chunks = grouper(max_elements_per_chunk, all_page_numbers)
		for chunk in chunks:
			thread = threading.Thread(target=self._download_images, args=(chunk, comic))
			threads.append(thread)

		self.logger.info(f'starting {len(threads)} threads')
		for thread in threads:
			thread.start()

		for index, thread in enumerate(threads):
			self.logger.info("joining thread %d." % index)
			thread.join()
			logging.info("Main    : thread %d done" % index)

	def _get_page_url(self, page_number, comic):
		"""
		checks target page and previous page for url of given page
		"""
		page = comic.getpage(page_number) 
		if page is not None and page.url is not None:
			return page.url

		prev_page = comic.getpage(page_number - 1)
		if prev_page is not None and prev_page.next_page_url is not None:
			return prev_page.next_page_url
		return None

class Comic:
	def __init__(self):
		self.pages = {}

	def addpage(self, page):
		self.pages[str(page.number)] = page

	def getpage(self, page_number):
		return self.pages.get(str(page_number))

@dataclass
class ComicPage:
	number: int
	url: str
	name: str = 'unknown'
	next_page_url: str = None
	image_url: str = None
	

class XkcdScraper(ComicScraper):

	def get_base_url(self):
		""" e.g. xkcd.com """
		return 'xkcd.com'

	def get_next_comic_url(self, page_soup, page_number):
		""" return the url of the page following the given page """
		next_link = page_soup.find('a', string="Next >")
		if next_link is not None:
			return self.get_base_url() + next_link['href']
		else:
			self.logger.warning(f'could not find next link for page {page_number}')
			return None

	def get_image_url(self, page_soup, page_number):
		""" return the image url on the given page """
		comicdiv = page_soup.find(id='comic')
		if comicdiv is None:
			self.logger.warning(f'could not find image div for page {page_number}')
			return None

		img = comicdiv.find('img')
		if img is None:
			self.logger.warning(f'could not find image element for page {page_number}')
			return None
		return img['src']

	def get_page_name(self, page_soup, page_number):
		""" return the string that you want to appear in the image file name for this page """
		comicdiv = page_soup.find(id='comic')
		if comicdiv is None:
			self.logger.warning(f'could not find image div for page {page_number}')
			return None

		img = comicdiv.find('img')
		if img is None:
			self.logger.warning(f'could not find image element for page {page_number}')
			return None

		return img['title']

	def guess_urls_from_page_number(self, page_number):
		""" return list of possible urls for the given page number, each will be tried e.g. ['xkcd.com/2249'] """
		return [f'xkcd.com/{page_number}']

class PbfScraper(ComicScraper):

	def get_base_url(self):
		""" e.g. xkcd.com """
		return 'pbfcomics.com'

	def get_next_comic_url(self, page_soup, page_number):
		""" return the url of the page following the given page """
		next_link = page_soup.find('a', rel="next")
		if next_link is not None:
			return next_link['href']
		else:
			self.logger.warning(f'could not find next link for page {page_number}')
			return None

	def get_image_url(self, page_soup, page_number):
		""" return the image url on the given page """
		comicdiv = page_soup.find(id='comic')
		if comicdiv is None:
			self.logger.warning(f'could not find image div for page {page_number}')
			return None

		img = comicdiv.find('img')
		if img is None:
			self.logger.warning(f'could not find image element for page {page_number}')
			return None
		return img['src']

	def get_page_name(self, page_soup, page_number):
		""" return the string that you want to appear in the image file name for this page """
		comicdiv = page_soup.find(id='comic')
		if comicdiv is None:
			self.logger.warning(f'could not find image div for page {page_number}')
			return None

		img = comicdiv.find('img')
		if img is None:
			self.logger.warning(f'could not find image element for page {page_number}')
			return None

		return img['title']

	def guess_urls_from_page_number(self, page_number):
		""" return list of possible urls for the given page number, each will be tried e.g. ['xkcd.com/2249'] """
		if page_number == 1:
			return [self.get_base_url() + '/comics/stiff-breeze']
		elif page_number == 7:
			# number six links to exposm
			return ['https://pbfcomics.com/comics/instant-bacon-2/']
		else:
			return []

	def is_last_page(self, page):
		""" return true if given ComicPage is the last page -- used to figure out when to stop when no stop page is given """
		return page.number != 6 and page.next_page_url is None

if __name__ == '__main__':
	logger = logging.getLogger(__name__)
	logger.setLevel(logging.DEBUG)
	formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

	scraper = PbfScraper()

	fh = logging.FileHandler(f'{scraper.get_base_url()}.log')
	fh.setFormatter(formatter)
	fh.setLevel(logging.DEBUG)
	logger.addHandler(fh)

	ch = logging.StreamHandler()
	ch.setLevel(logging.DEBUG)
	ch.setFormatter(formatter)
	logger.addHandler(ch)

	scraper.scrape(1,20)
	scraper.scrape()

