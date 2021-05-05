#  破解滑块验证码（geetest极验）

![](https://img.fythonfang.com/2021-05-01-103607_439x430_scrot.png)

最近写爬虫遇到极验（geetest）的滑块验证码，首先想到的是用[Selenium](https://selenium-python.readthedocs.io/)模拟人拖动滑块，那么问题来了其实主要解决下面两个问题

- 拖动的距离是多少
- 怎么模拟出像人一样再滑动

### 滑动距离

先来解决第一个问题，我们怎么计算拖动距离，打开chrome的审查元素查看需要拖动的图片

```html
<div class="geetest_canvas_img geetest_absolute" style="display: block;">
   <div class="geetest_slicebg geetest_absolute">
      <canvas class="geetest_canvas_bg geetest_absolute" height="160" width="260"></canvas>
      <canvas class="geetest_canvas_slice geetest_absolute" width="260" height="160"></canvas>
   </div>
   <canvas class="geetest_canvas_fullbg geetest_fade geetest_absolute" height="160" width="260" style="display: none;"></canvas>
</div>
```

发现有三个`canvas` 对应三张图片大小都是 260* 160 ，我们使用selenium执行 js 转成 base64 后再转成图片都保存下来看一下，第一张 *geetest_canvas_bg* 是有缺口的图片

```python
im_bg_b64 = driver.execute_script(
    'return document.getElementsByClassName("geetest_canvas_bg geetest_absolute")[0].toDataURL("image/png");')
# base64 encoded image
im_bg_b64 = im_bg_b64.split(',')[-1]
im_bg_bytes = base64.b64decode(im_bg_b64)
with open('./temp_bg.png', 'wb') as f:
    f.write(im_bg_bytes)
```

![](https://img.fythonfang.com/temp_bg.png)

然后第二张 *geetest_canvas_slice* 根据上面相同的方法保存到本地是这样的，就是一个滑块

![](https://img.fythonfang.com/temp_slice.png)

第三张 *geetest_canvas_fullbg* 猜名称也能猜到是图片的全景

![](https://img.fythonfang.com/temp_fullbg.png)

有上面三张图片，怎么计算滑动的距离呢，发现只要找到第一张缺口的位置坐标 x1 和第二张滑块的坐标 x2 那么 x1 - x2 就是我们要的距离，主要是找到 x1 的位置可以通过对比第一张和第三张得到，具体的方法是对比两张图像素点不同时即为 x1 的位置。因为 x2 的位置一直在左边差不多固定的位置假设离最左边为 10 个像素所以我们不需要计算 x2，以下是实现两张图片确定 x1 的代码，图片处理使用的是[pillow](https://pillow.readthedocs.io/en/stable/)库

```python
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
```

上面可以得出 x1，然后 x1 - 10 就是所需要的滑动的距离了

### 模拟滑动

第一个问题解决了得到了滑动距离 x， 那怎么模拟人为的滑动呢。经过简单测试发现机器只要像人一样一下划过去多一点然后再收一点回来就可以骗过机器，代码如下，主要用到selenium的`ActionChains`。也有人尝试加上加速度，因为我测试下来这也可以我又非常懒就没加了。。。

```python
def simulate_human_drag_x(self, element, offset_x):
    """
    简单拖拽模仿人的拖拽：快速沿着X轴拖动，多拖一点然后再回来，再暂停，释放
    """
    action_chains = webdriver.ActionChains(driver)
    # 点击，准备拖拽
    action_chains.click_and_hold(element)
    action_chains.pause(0.3)
    action_chains.move_by_offset(offset_x + 7, 0)
    action_chains.pause(0.8)
    action_chains.move_by_offset(-7, 0)
    action_chains.pause(0.6)
    action_chains.release()
    action_chains.perform()
```

### 验证

按照上面的思路串起来，再加上失败重试（点击刷新按钮）就差不多，下面以注册极验账户[https://www.geetest.com/Register](https://www.geetest.com/Register)测试下。代码可以直接运行，[GitHub]()链接

```python
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

```


