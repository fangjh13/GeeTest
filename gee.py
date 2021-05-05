from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import base64
from PIL import Image
from io import BytesIO


class GeetestCaptcha:
    def __init__(self, driver):
        self.driver = driver

    def crack_geetest_captcha(self, try_time=5):
        """
        模拟滑动GeeTest滑动验证码
        """
        print(f"try crack captcha, remain {try_time} times")
        # 等待图片刷新
        time.sleep(3)
        WebDriverWait(self.driver, 20).until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "canvas.geetest_canvas_slice.geetest_absolute")))
        im_bg_b64 = self.driver.execute_script(
            'return document.getElementsByClassName("geetest_canvas_bg geetest_absolute")[0].toDataURL("image/png");')
        # base64 encoded image
        im_bg_b64 = im_bg_b64.split(',')[-1]
        im_bg_bytes = base64.b64decode(im_bg_b64)
        # with open('./temp_bg.png', 'wb') as f:
        #     f.write(im_bg_bytes)
        # im_slice_b64 = self.driver.execute_script(
        #     'return document.getElementsByClassName("geetest_canvas_slice geetest_absolute")[0].toDataURL("image/png");')
        # im_slice_b64 = im_slice_b64.split(',')[-1]
        # im_slice_bytes = base64.b64decode(im_slice_b64)
        # with open('./temp_slice.png', 'wb') as f:
        #     f.write(im_slice_bytes)
        im_fullbg = self.driver.execute_script(
            'return document.getElementsByClassName("geetest_canvas_fullbg geetest_fade geetest_absolute")[0].toDataURL("image/png");')
        im_fullbg = im_fullbg.split(',')[-1]
        im_fullbg_bytes = base64.b64decode(im_fullbg)
        # with open('./temp_fullbg.png', 'wb') as f:
        #     f.write(im_fullbg_bytes)
        # calculate sliding distance
        im_bg = Image.open(BytesIO(im_bg_bytes))
        im_fullbg = Image.open(BytesIO(im_fullbg_bytes))
        # 计算距离
        x_offset = self.get_dis_use_same_pixel(im_fullbg, im_bg)
        # 根据距离滑动滑块
        if x_offset is not None:
            WebDriverWait(self.driver, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".geetest_slider_button")))
            button = self.driver.find_element_by_css_selector(".geetest_slider_button")
            # 滑块距离左边有 10 像素左右，需要减掉
            x_offset -= 10
            print(f"slide {x_offset} pixel")
            self.simulate_human_drag_x(button, x_offset)
            time.sleep(3)
            if 'geetest_panel_box geetest_panelshowslide' not in self.driver.page_source:
                print('crack success')
                return True
            if len(self.driver.find_elements_by_xpath("//div[@class='geetest_panel_box geetest_panelshowslide']")) > 0 and \
                    try_time > 0:
                WebDriverWait(self.driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//a[@class='geetest_refresh_1']"))).click()
                return self.crack_geetest_captcha(try_time - 1)
            print("sorry! failed to crack")
            return False
        else:
            print("failed to calculate pixel distance")

        # 没计算出滑动距离。继续刷新下尝试
        if try_time > 0:
            time.sleep(2)
            WebDriverWait(self.driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//a[@class='geetest_refresh_1']"))).click()
            return self.crack_geetest_captcha(try_time - 1)
        else:
            print("sorry! no chance. failed")
            return False

    def simulate_human_drag_x(self, element, offset_x):
        """
        简单拖拽模仿人的拖拽：快速沿着X轴拖动，多拖一点然后再回来，再暂停，释放
        """
        action_chains = webdriver.ActionChains(self.driver)
        # 点击，准备拖拽
        action_chains.click_and_hold(element)
        action_chains.pause(0.3)
        action_chains.move_by_offset(offset_x + 7, 0)
        action_chains.pause(0.8)
        action_chains.move_by_offset(-7, 0)
        action_chains.pause(0.6)
        action_chains.release()
        action_chains.perform()

    def get_dis_use_same_pixel(self, im_fullbg, im_bg):
        """
        对比是否是相同像素确定移动距离
        """
        pix_1 = im_fullbg.load()
        pix_2 = im_bg.load()
        threshold = 60

        for x in range(im_fullbg.size[0]):
            # 垂直方向不同像素的计数
            vert_count = 0
            for y in range(im_fullbg.size[1]):
                p_1 = pix_1[x, y]
                p_2 = pix_2[x, y]
                # 找到像素不同的点
                if abs(p_1[0] - p_2[0]) > threshold and abs(p_1[1] - p_2[1]) > threshold and abs(p_1[2] - p_2[2]) > threshold:
                    vert_count += 1
                    # 如果是一条直线返回横坐标距离，测试下来10个像素结果较好
                    # print(vert_count, x)
                    if vert_count > 10:
                        return x

options = webdriver.ChromeOptions()
# options.add_argument("--headless")     # Runs Chrome in headless mode.
options.add_argument('--no-sandbox')  # Bypass OS security model
# options.add_argument('--disable-gpu')  # applicable to windows os only
options.add_argument('--ignore-certificate-errors')
options.add_argument("--disable-extensions")
options.add_argument('start-maximized')
options.add_argument('disable-infobars')

# Configure capabilities
capabilities = webdriver.DesiredCapabilities.CHROME
driver = webdriver.Chrome(executable_path="/usr/bin/chromedriver",
                          options=options,
                          desired_capabilities=capabilities)
driver.set_script_timeout(120)
driver.set_page_load_timeout(120)
driver.get("https://www.geetest.com/Register")
WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//div[@id="gt-register-mobile"]//input[@placeholder="手机号码"]')))
driver.find_element_by_xpath('//div[@id="gt-register-mobile"]//input[@placeholder="手机号码"]').send_keys('13799999999')
WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//div[@id="gt-register-mobile"]//div[@class="sendCode"]')))
driver.find_element_by_xpath('//div[@id="gt-register-mobile"]//div[@class="sendCode"]').click()
WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.XPATH, "//canvas[@class='geetest_canvas_bg geetest_absolute']")))

GeetestCaptcha(driver).crack_geetest_captcha()

