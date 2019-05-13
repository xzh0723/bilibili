# -*- coding: utf-8 -*-
import re
import time
import json
import math
import requests
from scrapy import Spider, Request, http
from bilibili.items import *
from lxml import etree
from bilibili.view import showcloud

class Top100Spider(Spider):
    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
    name = 'top100'
    allowed_domains = ['www.bilibili.com']
    base_url = 'https://www.bilibili.com/ranking/all/{}/0/3'

    def start_requests(self):
        for type in self.settings.get('TYPE'):
            yield Request(self.base_url.format(type), headers=self.settings.get('HEADERS'), callback=self.parse)

    def parse(self, response):
        videos = response.xpath('//ul[@class="rank-list"]/li')
        for video in videos:
            item = VideoItem()
            field_map = {
                'rank': './div[1]/text()',
                'title': './/div[@class="info"]/a/text()',
                'src': './/div[@class="info"]/a/@href',
                'img': './/div[contains(@class, "lazy-img")]/img/@src',
                'play': './/div[@class="detail"]/span[1]/text()',
                'comment': './/div[@class="detail"]/span[2]/text()',
                'author': './/div[@class="detail"]/a/span/text()',
                'score': './/div[@class="pts"]/div/text()'
            }
            for field, attr in field_map.items():
                item[field] = ''.join(video.xpath(attr).extract()).strip()

            # 获取视频下载地址，这个地址是视频观看页面在F12模式下刷新得到的新页面地址，请求这个页面返回的响应中有视频下载地址
            url = 'https://m.bilibili.com' + re.findall(r'.*?com(.*)/', item['src'])[0] + '.html'
            #url = 'https:' + item['src']
            response = requests.get(url, headers=self.settings.get('HEADERS'))
            html = etree.HTML(response.text)
            video_url = re.findall('.*?url":"(.*?)".*', html.xpath('//script[3]/text()')[0], re.S)[0]
            #video_url = re.findall('.*?baseUrl":"(.*?)".*', response.text, re.S)[0]
            item['video_url'] = video_url
            yield item

            # 弹幕API
            cid = re.findall('.*/(\d+)-.*', video_url)[0]
            danmu_url = 'https://comment.bilibili.com/{}.xml'.format(cid)
            yield Request(danmu_url, headers=self.settings.get('HEADERS'), meta={'title': item['title']},
                          callback=self.parse_danmu, dont_filter=True)

            # 评论API，注意这里不能直接用https://api.bilibili.com/x/v2/reply?callback=jQuery17208359418896210684_1557746685098&jsonp=jsonp&pn=2&type=1&oid=52012946&sort=0&_=1557748994898
            # 这个API只能留我下面这三个参数才可以请求成功，我也不知道为什么哈哈
            oid = re.findall('.*av(\d+)/', item['src'])[0]
            comment_url = 'https://api.bilibili.com/x/v2/reply?pn={}&type=1&oid={}'.format(1, oid)
            yield Request(comment_url, headers=self.settings.get('HEADERS'),
                          meta={'title': item['title'], 'page': 1, 'oid': oid},
                            callback=self.parse_comment, dont_filter=True)

    def parse_danmu(self, response):
        item = DanmusItem()
        item['title'] = response.meta.get('title')
        danmus = []
        # 注意：这里返回的是XmlResponse，要进行xml文件解码，如下所示
        # scrapy的三种响应形式：TextResponse, HtmlResponse, XmlResponse 均可以用这种解码方式
        response = http.XmlResponse(url=response.url, body=response.body, encoding='utf-8')
        ds = re.findall(r'<d(.*?)</d>', response.text, re.S)
        for d in ds:
            time = re.findall(r'p="(\d+.\d+),.*', d)[0]
            m, s = divmod(float(time), 60)
            sending_time = '%02d:%02d' % (m, s)
            content = re.findall('.*>(.*)', d)[0]
            danmu = {}
            danmu[sending_time] = content
            danmus.append(danmu)
        item['danmus'] = danmus
        yield item

    def parse_comment(self, response):
        item = CommentItem()
        result = json.loads(response.text)
        if result.get('data') and result.get('data').get('replies'):
            acount = result.get('data').get('page').get('acount')
            MAX_PAGE_NUM = math.ceil(int(acount) / 20)
            comments = result.get('data').get('replies')
            for comment in comments:
                item['title'] = response.meta.get('title')
                item['content'] = comment.get('content').get('message').replace('\n', '')
                # 将时间戳转化为时间
                timeStamp = comment.get('ctime')
                timeArray = time.localtime(timeStamp)
                item['time'] = time.strftime("%Y--%m--%d %H:%M:%S", timeArray)
                item['like'] = comment.get('like')
                item['user_info'] = {
                    'uid': comment.get('member').get('uid'),
                    'name': comment.get('member').get('uname'),
                    'sex': comment.get('member').get('sex'),
                    'avatar': comment.get('member').get('avatar'),
                    'sign': comment.get('member').get('sign')
                }
                yield item

            # 下一页
            page = response.meta.get('page')
            oid = response.meta.get('oid')
            page += 1
            if page <= MAX_PAGE_NUM:
                comment_url = 'https://api.bilibili.com/x/v2/reply?pn={}&type=1&oid={}'.format(page, oid)
                yield Request(comment_url, headers=self.settings.get('HEADERS'),
                              meta={'title': item['title'], 'page': page, 'oid': oid},
                              callback=self.parse_comment, dont_filter=True)

    def close(self, reason):
        """
        :param reason: 词云
        :return:
        """
        showcloud()

