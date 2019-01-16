# -*- coding: utf-8 -*-
import os
import json
import time
from pprint import pprint
from bs4 import BeautifulSoup
from JD_Stocking.items import JdStockingItem

import scrapy
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    NoSuchElementException,
    StaleElementReferenceException
)

def gen_browser(driver_path):
    '''实例化一个driver'''
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('disable-infobars')
    options.add_argument("--disable-plugins-discovery")
    user_agent = "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.67 Safari/537.36"
    options.add_argument('user-agent="{0}"'.format(user_agent))
    # ############### 专业造假 ***************************
    def send(driver, cmd, params={}):
        '''
        向调试工具发送指令
        from: https://stackoverflow.com/questions/47297877/to-set-mutationobserver-how-to-inject-javascript-before-page-loading-using-sele/47298910#47298910
        '''
        resource = "/session/%s/chromium/send_command_and_get_result" % driver.session_id
        url = driver.command_executor._url + resource
        body = json.dumps({'cmd': cmd, 'params': params})
        response = driver.command_executor._request('POST', url, body)
        if response['status']:
            raise Exception(response.get('value'))
        return response.get('value')
    def add_script(driver, script):
        '''在页面加载前执行js'''
        send(driver, "Page.addScriptToEvaluateOnNewDocument", {"source": script})
    # 给 webdriver.Chrome 添加一个名为 add_script 的方法
    webdriver.Chrome.add_script = add_script # 这里（webdriver.Chrome）可能需要改，当调用不同的驱动时
    # *************** 专业造假 ###################
    browser = webdriver.Chrome(
        executable_path=driver_path,
        chrome_options=options
    )
    # ################## 辅助调试 *********************
    existed = {
        'executor_url': browser.command_executor._url,  # 浏览器可被远程连接调用的地址
        'session_id': browser.session_id  # 浏览器会话ID
    }
    # pprint(existed)
    # ********************* 辅助调试 ##################
    # ############### 专业造假 ***************************
    browser.add_script("""
    Object.defineProperty(navigator, 'webdriver', {
        get: () => false,
    });
    window.navigator.chrome = {
        runtime: {},
    };
    Object.defineProperty(navigator, 'languages', {
        get: () => ['zh-CN', 'zh']
    });
    Object.defineProperty(navigator, 'plugins', {
        get: () => [0, 1, 2],
    });
    """)
    # *************** 专业造假 ###################

    return browser

class FoodspiderSpider(scrapy.Spider):
    name = 'FoodSpider'
    allowed_domains = ['jd.com']
    start_urls = ['https://search.jd.com/Search?keyword=%E5%B9%B4%E8%B4%A7%E5%A4%A7%E7%A4%BC%E5%8C%85&enc=utf-8&qrst=1&rt=1&stop=1&spm=2.1.0&vt=2&stock=1&page=2&s=1&click=0']

    def parse(self, response):

        # 取得配置文件中自己定义的自动化工具路径
        driver_path = self.settings.get('DRIVER_PATH')
        # import ipdb; ipdb.set_trace()
        browser = gen_browser(driver_path)

        # 打开页面
        browser.get(response.url)  

        # 慢慢往下滚
        for num in range(1000, 10000, 1000):
            browser.execute_script("window.scrollTo(0, {0})".format(num))
            time.sleep(0.5)

        # 缓冲一秒
        time.sleep(1)

        print('*' * 20, len(browser.find_elements_by_css_selector('.p-name.p-name-type-2')))
        items = browser.find_elements_by_css_selector('.gl-warp.clearfix > li')
        for content in items:
            item = JdStockingItem()
            item['name'] = content.find_element_by_css_selector('.p-name em').text.replace('\n', '-')  # 标题
            item['price'] = content.find_element_by_css_selector('.p-price strong').text  # 价格
            item['url'] = content.find_element_by_css_selector('a').get_attribute("href")  # 链接
            item['pingjia'] = content.find_element_by_css_selector('.p-commit strong').text  # 评价
            item['dianpu'] = content.find_element_by_css_selector('.p-shop span').text  # 店铺
            item['img'] = content.find_element_by_css_selector('.p-img img').get_attribute("src")  # 图片

            print({
                '标题': item['name'],
                '价格': item['price'],
                '链接': item['url'],
                '评价': item['pingjia'],
                '店铺': item['dianpu'],
                '图片': item['img']
            })

            yield item
        # import ipdb as pdb; pdb.set_trace()