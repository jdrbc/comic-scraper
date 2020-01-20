from comicscraper import *

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

if __name__ == '__main__':
	scraper = XkcdScraper()
	scraper.enable_logging()
	scraper.scrape(1,20)
