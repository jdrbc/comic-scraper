# comic-scraper

Web comic scraper that uses shelve to recover past work

example usage


	# scraper code above

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

		# scrape first 20 pages
		scraper.scrape(1,20)

		# scrape whole site
		scraper.scrape()