import datetime
import re

import scrapy
from scrapy.exceptions import CloseSpider

from scrapy.loader import ItemLoader

from ..items import SwedbanklvItem
from itemloaders.processors import TakeFirst

import requests

url = "https://www.swedbank.lv/private/home/more/newsandblog/news"

base_payload = "request_timestamp=Mon+Mar+22+2021+13%3A50%3A08+GMT%2B0200+(Eastern+European+Standard+Time)&pageId=controls&securityId=&encoding=UTF-8&language=LAT&controlId=news.NewsListControl&keywords=IBANK_PRIVATE_NEWS&startYear=2001&layout=archive&dateToken={}.{}"
headers = {
  'Connection': 'keep-alive',
  'Pragma': 'no-cache',
  'Cache-Control': 'no-cache',
  'sec-ch-ua': '"Google Chrome";v="89", "Chromium";v="89", ";Not A Brand";v="99"',
  'Accept': '*/*',
  'X-Requested-With': 'XMLHttpRequest',
  'sec-ch-ua-mobile': '?0',
  'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36',
  'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
  'Origin': 'https://www.swedbank.lv',
  'Sec-Fetch-Site': 'same-origin',
  'Sec-Fetch-Mode': 'cors',
  'Sec-Fetch-Dest': 'empty',
  'Referer': 'https://www.swedbank.lv/private/home/more/newsandblog/news',
  'Accept-Language': 'en-US,en;q=0.9,bg;q=0.8',
  'Cookie': 'lastApp=private; hanza=62SiSQAtN7tUbOvhe6h23Q; spa=true; language=lv; TS01465fb3=01791fa7eb572e1e48d1276d3160699d6bce75523c5b368ccac21009702e41fab82c2d6d225018c5dd886349dd79b5cba4b7e921f7; COOKIE_CONSENT={"NECESSARY":1,"ANALYTICAL":1,"TARGETING":1}; scp=6578570d-4de8-42bb-87bb-b8fa79b11796; scpa=true; AMCVS_AB12899B544ABE260A4C98BC%40AdobeOrg=1; AMCV_AB12899B544ABE260A4C98BC%40AdobeOrg=-330454231%7CMCMID%7C61855805862685888201285566088112687732%7CMCAAMLH-1617018202%7C6%7CMCAAMB-1617018202%7C6G1ynYcLPuiQxYZrsz_pkqfLG9yMXBpb2zX5dvJdYQJzPXImdj0y%7CMCOPTOUT-1616420602s%7CNONE%7CvVersion%7C3.1.2; s_cc=true; windowWidth=1324; windowHeight=977'
}


class SwedbanklvSpider(scrapy.Spider):
	name = 'swedbanklv'
	start_urls = ['https://www.swedbank.lv/private/home/more/newsandblog/news']
	year = int(datetime.datetime.now().year)
	month = int(datetime.datetime.now().month)

	def parse(self, response):
		payload = base_payload.format(self.month, self.year)
		data = requests.request("POST", url, headers=headers, data=payload)
		raw_data = scrapy.Selector(text=data.text)
		post_links = raw_data.xpath('//div[@id="newsArchiveContainer"]/ul[contains(@class, "news-list")]//a/@href').getall()

		post_payload = "request_timestamp=Mon+Mar+22+2021+14%3A26%3A43+GMT%2B0200+(Eastern+European+Standard+Time)&pageId=controls&securityId=&encoding=UTF-8&language=LAT&controlId=news.NewsDetailsControl&layout=details&newsId={}"

		for post in post_links:
			link_id = re.findall(r'\d+', post)[0]
			link = f'https://www.swedbank.lv/private/home/more/newsandblog/news#news={link_id}'
			date = datetime.datetime.strptime(link_id[:14], '%Y%m%d%H%M%S')
			yield response.follow(link, self.parse_post, cb_kwargs={'date': date, 'payload': post_payload.format(link_id)} ,dont_filter=True)

		self.month -= 1
		if self.month == 3 and self.year == 2016:
			raise CloseSpider('no more pages')
		if self.month == 0:
			self.month = 12
			self.year -= 1

		yield response.follow(response.url, self.parse, dont_filter=True)

	def parse_post(self, response, date, payload):
		data = requests.request("POST", url, headers=headers, data=payload)
		raw_data = scrapy.Selector(text=data.text)

		title = raw_data.xpath('//h2/text()').get()
		description = raw_data.xpath('//p//text()[normalize-space()]').getall()
		description = [p.strip() for p in description]
		description = ' '.join(description).strip()

		item = ItemLoader(item=SwedbanklvItem(), response=response)
		item.default_output_processor = TakeFirst()
		item.add_value('title', title)
		item.add_value('description', description)
		item.add_value('date', date)

		return item.load_item()
