# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
import os
import pymongo
import requests
from logging import getLogger
from bilibili.items import *


class DownloadPipeline(object):
    def __init__(self, headers):
        self.logger = getLogger(__name__)
        self.headers = headers

    def process_item(self, item, spider):
        if isinstance(item, VideoItem):
            video_url = item['video_url']
            response = requests.get(video_url, headers=self.headers)
            if response.status_code == 200:
                path = os.path.abspath('...')
                save_path = path + '\\B站top100'
                if not os.path.exists(save_path):
                    os.mkdir(save_path)
                    self.logger.debug('文件夹创建成功!')
                save_video = save_path + '\\' + item['title'] + '.mp4'
                self.logger.debug('开始下载%s' % item['title'])
                with open(save_video, 'wb') as f:
                    f.write(response.content)
                    self.logger.debug('下载成功！')
            else:
                self.logger.debug('下载失败')
        return item

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            headers=crawler.settings.get('HEADERS'),
        )

class MongoPipeline(object):
    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]

    def process_item(self, item, spider):
        #if isinstance(item, VideoItem) or isinstance(item, DanmusItem) or isinstance(item, CommentItem):
        self.db[item.collection].insert(dict(item))
        return item

    def close_spider(self, spider):
        self.client.close()

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get('MONGO_URI'),
            mongo_db=crawler.settings.get('MONGO_DB')
        )

class TextPipeline(object):
    def open_spider(self, spider):
        self.file = open('./utils/danmu.txt', 'a', encoding='utf-8')

    def process_item(self, item, spider):
        if isinstance(item, DanmusItem):
            danmus = item['danmus']
            string = ''
            for danmu in danmus:
                for k, v in danmu.items():
                    string += v + '\n'
            self.file.write(string)
        # return item 必须要在函数第一个后tab处，不然返回回去之后变成None了。。
        return item
