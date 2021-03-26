import logging
import re

import unicodedata
from lxml import etree
from ruia import Spider, Request, Response

from middlewares import middleware
from mongo_db import MotorBase

logger = logging.getLogger(__name__)
logger.propagate = False


class CategorySpider(Spider):
    name = "Categories"
    start_urls = ["https://www.facebook.com/pages/category/"]
    request_config = {"RETRIES": 3, "DELAY": 0, "TIMEOUT": 5}
    step = 10
    # aiohttp_kwargs = {"timeout": 5}

    def check_response(self, response_text):
        if len(response_text) < 200000:
            return False
        return True

    async def parse(self, response: Response):
        self.mongo_db = MotorBase().get_db("facebook")
        response_text = await response.text()
        response_metadata = response.metadata
        logger.info(f'get {response.url} {len(response_text)}')
        category = response_metadata.get('category')
        page_num = response_metadata.get('page_num')
        url = response.url
        logging.info(f'get {response.url} {len(response_text)}')
        try:
            target = re.search('<!--([\s\S]*)-->', response_text).group(1)
        except AttributeError:
            logger.warning(f'No target in this page {url}')
            retry_times = response_metadata.get('retry_times', 0)
            if retry_times < self.request_config.get('RETRIES'):
                response_metadata['retry_times'] = retry_times
                yield Request(response.url, callback=self.parse_about_page, metadata=response_metadata)
        target_tree = etree.HTML(target)
        all_divs = target_tree.xpath('./body/div')
        logger.info(f'got {len(all_divs) - 2} row, url: {url}')
        # parse_result = []
        for row_div in all_divs[1:-1]:
            try:
                left_div, right_div = row_div.xpath('./div/div')
            except ValueError:
                logger.error(f'failed while split divs: {url}')
                continue
            try:
                # img_url = left_div.xpath('.//img/@src')[0]
                page_url = left_div.xpath('.//a/@href')[0]
            except IndexError:
                logger.warning(f'failed while parse left div: {url}')
                continue
            try:
                name_div, brief_div = right_div.getchildren()
                # likes_text = right_div.xpath('./text()')[0]
                # likes_text = unicodedata.normalize('NFKC', likes_text)
                page_name = name_div.xpath('.//text()')[1]
                page_name = unicodedata.normalize('NFKC', page_name)
            except IndexError:
                logger.warning(f'failed while parse right div: {url}')
                continue
            # parse_result.append({
            #     'curl': url,
            #     # 'likes': likes_text,
            #     'pname': page_name,
            #     'purl': page_url,
            #     # 'img_url': img_url,
            # })
            data = {
                'curl': url,
                'pname': page_name,
                'purl': page_url,
            }
            logger.info(f'got {page_name} in url: {url} page_url: {page_url} {data}')
            yield Request(page_url, callback=self.parse_about_page, metadata=data)

        # if self.check_response(response_text):
        print(all_divs)
        if all_divs:
            next_page_num = page_num + self.step
            page_url = f'https://www.facebook.com/pages/category/{category}/?page={next_page_num}'
            # yield Request(page_url, callback=self.parse, metadata={
            #             'category': category,
            #             'page_num': next_page_num
            #         })
            if page_num != 1:
                # 往回爬取
                for gen_page_num in range(page_num - self.step + 1, page_num):
                    page_url = f'https://www.facebook.com/pages/category/{category}/?page={gen_page_num}'
                    # yield Request(page_url, callback=self.parse, metadata={
                    #     'category': category,
                    #     'page_num': gen_page_num
                    # })

    async def parse_about_page(self, response: Response):
        resp_text = await response.text()
        url = response.url
        response_metadata = response.metadata
        logger.info(f'get {len(resp_text)} {response.status} url: {url}')
        try:
            page_id = re.search('/pages/suggest/edits/dialog/\?page_id=(\d+)', resp_text).group(1)
        except:
            logger.warning(f'not page id in {url}')
            retry_times = response_metadata.get('retry_times', 0)
            if retry_times < self.request_config.get('RETRIES'):
                response_metadata['retry_times'] = retry_times
                yield Request(response.url, callback=self.parse_about_page, metadata=response_metadata)
        else:
            response_metadata['pid'] = page_id
            yield self.process_item(data=response_metadata)

    async def process_item(self, data: dict):
        try:
            await self.mongo_db.news.update_one(
                {"pid": data.get('pid')},
                {"$set": data},
                upsert=True
            )
        except Exception as e:
            self.logger.exception(e)


if __name__ == '__main__':
    CategorySpider.start_urls = [f'https://www.facebook.com/pages/category/forestry-logging/']
    CategorySpider.metadata = {'category': 'forestry-logging', 'page_num': 1}
    CategorySpider.start(middleware=middleware)
