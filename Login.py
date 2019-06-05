from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
import time
import random
from PIL import Image
from io import BytesIO

THRESHOLD = 60
LEFT = 60
BORDER = 0


class BiliBili():
    def __init__(self, username, password):
        self.url = "https://passport.bilibili.com/login"
        options = webdriver.ChromeOptions()
        # 设置为开发者模式，避免被识别
        # options.add_experimental_option('excludeSwitches', ['enable-automation'])
        self.browser = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.browser, 20)
        self.username = username
        self.password = password

    def __del__(self):
        self.browser.close()

    def login(self):
        """
        打开浏览器,并且输入账号密码
        :return: None
        """
        self.browser.get(self.url)
        username = self.wait.until(EC.element_to_be_clickable((By.ID, 'login-username')))
        password = self.wait.until(EC.element_to_be_clickable((By.ID, 'login-passwd')))
        submit = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.btn-login')))
        time.sleep(1)
        username.send_keys(self.username)
        time.sleep(1)
        password.send_keys(self.password)
        time.sleep(1)
        submit.click()

    def get_geetest_button(self):
        button = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'geetest_slider_button')))
        return button

    def get_geetest_image(self, name, full):
        top, bottom, left, right, size = self.get_position(full)
        # print("验证码位置", top, bottom, left, right)
        screenshot = self.get_screenshot()
        captcha = screenshot.crop(
            (left, top, right, bottom))
        size = size["width"] - 1, size["height"] - 1
        captcha.thumbnail(size)
        # captcha.show()
        # captcha.save(name)
        return captcha

    def get_position(self, full):
        img = self.wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "canvas.geetest_canvas_slice")))
        fullbg = self.wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "canvas.geetest_canvas_fullbg")))
        time.sleep(2)
        
        # 两种执行js写法
        if full:
            self.browser.execute_script(
                'document.getElementsByClassName("geetest_canvas_fullbg")[0].setAttribute("style", "")')
        else:
            self.browser.execute_script(
                "arguments[0].setAttribute(arguments[1], arguments[2])", fullbg, "style", "display: none")

        location = img.location
        size = img.size
        top, bottom, left, right = location["y"], location["y"] + \
                                   size["height"], location["x"], location["x"] + size["width"]
        return (top, bottom, left, right, size)

    def get_screenshot(self):
        screenshot = self.browser.get_screenshot_as_png()
        return Image.open(BytesIO(screenshot))

    def get_gap(self, image1, image2):
        for i in range(LEFT, image1.size[0]):
            for j in range(image1.size[1]):
                if not self.is_pixel_equal(image1, image2, i, j):
                    return i
        return LEFT

    def is_pixel_equal(self, image1, image2, x, y):
        pixel1 = image1.load()[x, y]
        pixel2 = image2.load()[x, y]
        if abs(pixel1[0] - pixel2[0]) < THRESHOLD and abs(pixel1[1] - pixel2[1]) < THRESHOLD and abs(
                pixel1[2] - pixel2[2]) < THRESHOLD:
            return True
        else:
            return False

    def get_track(self, distance):
        """
        获取滑块移动轨迹的列表
        :param distance: 第二个缺块的左侧的x坐标
        :return: 滑块移动轨迹列表
        """
        track = []
        current = 0
        mid = distance * 2 / 3
        t = 0.2
        v = 0
        distance += 10  # 使滑块划过目标地点, 然后回退
        while current < distance:
            if current < mid:
                a = random.randint(1, 3)
            else:
                a = -random.randint(3, 5)
            v0 = v
            v = v0 + a * t
            move = v0 * t + 0.5 * a * t * t
            current += move
            track.append(round(move))
        for i in range(2):
            track.append(-random.randint(2, 3))
        for i in range(2):
            track.append(-random.randint(1, 4))
        return track

    def get_slider(self):
        return self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "geetest_slider_button")))

    def move_to_gap(self, button, track):
        ActionChains(self.browser).click_and_hold(button).perform()
        for i in track:
            ActionChains(self.browser).move_by_offset(xoffset=i, yoffset=0).perform()
            time.sleep(0.0005)
        time.sleep(0.5)
        ActionChains(self.browser).release().perform()

    def get_cookies(self):
        cookies = ''
        cookies_list = self.browser.get_cookies()
        for i in cookies_list:
            cookies += i['name'] + '=' + i['value'] + '; '
        with open('cookies.txt', 'w', encoding='utf-8') as f:
            f.write(cookies)

    def crack(self):
        self.login()
        image1 = self.get_geetest_image("captcha1.png", True)
        image2 = self.get_geetest_image("captcha2.png", False)
        gap = self.get_gap(image1, image2)
        print("缺口位置", gap)
        track = self.get_track(gap - BORDER)
        print("滑动轨迹", track)
        slider = self.get_slider()
        self.move_to_gap(slider, track)
        time.sleep(1)

        try:
            # 检查是否成功登录进入主页
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'head-logo')))
            print('登录成功，保存cookies')
            self.get_cookies()
        except Exception:
            print('失败重试')
            self.crack()

if __name__ == '__main__':
    ACCOUNT = input('请输入您的账号:')
    PASSOWRD = input('请输入您的密码:')

    test = BiliBili(ACCOUNT, PASSOWRD)  # 输入账号和密码
    test.crack()
