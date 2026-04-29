# encoding=utf8
import io
import re
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By

def zodgame_checkin(driver, formhash):
    checkin_url = "https://zodgame.xyz/plugin.php?id=dsu_paulsign:sign&operation=qiandao&infloat=1&inajax=0"    
    checkin_query = """
        (function (){
        var request = new XMLHttpRequest();
        var fd = new FormData();
        fd.append("formhash","%s");
        fd.append("qdxq","kx");
        request.open("POST","%s",false);
        request.withCredentials=true;
        request.send(fd);
        return request;
        })();
        """ % (formhash, checkin_url)
    checkin_query = checkin_query.replace("\n", "")
    driver.set_script_timeout(240)
    resp = driver.execute_script("return " + checkin_query)
    match = re.search('<div class="c">\r\n(.*?)</div>\r\n', resp["response"], re.S)
    message = match[1] if match is not None else "签到失败"
    print(f"【签到】{message}")
    return "恭喜你签到成功!" in message or "您今日已经签到，请明天再来" in message


def zodgame_task(driver, formhash):

    def clear_handles(driver, main_handle):
        handles = driver.window_handles[:]
        for handle in handles:
            if handle != main_handle:
                driver.switch_to.window(handle)
                driver.close()
        driver.switch_to.window(main_handle)
      
    def show_task_reward(driver):
        driver.get("https://zodgame.xyz/plugin.php?id=jnbux")
        try:
            WebDriverWait(driver, 240).until(
                lambda x: x.title != "Just a moment..."
            )
            reward = driver.find_element(By.XPATH, '//li[contains(text(), "点币: ")]').get_attribute("textContent")[:-2]
            print(f"【Log】{reward}")
        except:
            pass

    driver.get("https://zodgame.xyz/plugin.php?id=jnbux")
    WebDriverWait(driver, 240).until(
        lambda x: x.title != "Just a moment..."
    )

    join_bux = driver.find_elements(By.XPATH, '//font[text()="开始参与任务"]')
    if len(join_bux) != 0 :    
        driver.get(f"https://zodgame.xyz/plugin.php?id=jnbux:jnbux&do=join&formhash={formhash}")
        WebDriverWait(driver, 240).until(
            lambda x: x.title != "Just a moment..."
        )
        driver.get("https://zodgame.xyz/plugin.php?id=jnbux")
        WebDriverWait(driver, 240).until(
            lambda x: x.title != "Just a moment..."
        )

    join_task_a = driver.find_elements(By.XPATH, '//a[text()="参与任务"]')
    success = True

    if len(join_task_a) == 0:
        print("【任务】所有任务均已完成。")
        return success
    handle = driver.current_window_handle
    for idx, a in enumerate(join_task_a):
        on_click = a.get_attribute("onclick")
        try:
            function = re.search("""openNewWindow(.*?)\(\)""", on_click, re.S)[0]
            script = driver.find_element(By.XPATH, f'//script[contains(text(), "{function}")]').get_attribute("text")
            task_url = re.search("""window.open\("(.*)", "newwindow"\)""", script, re.S)[1]
            driver.execute_script(f"""window.open("https://zodgame.xyz/{task_url}")""")
            driver.switch_to.window(driver.window_handles[-1])
            try:
                WebDriverWait(driver, 240).until(
                    lambda x: x.find_elements(By.XPATH, '//div[text()="成功！"]')
                )
            except:
                print(f"【Log】任务 {idx+1} 广告页检查失败。")
                pass

            try:     
                check_url = re.search("""showWindow\('check', '(.*)'\);""", on_click, re.S)[1]
                driver.get(f"https://zodgame.xyz/{check_url}")
                WebDriverWait(driver, 240).until(
                    lambda x: len(x.find_elements(By.XPATH, '//p[contains(text(), "检查成功, 积分已经加入您的帐户中")]')) != 0 
                        or x.title == "BUX广告点击赚积分 - ZodGame论坛 - Powered by Discuz!"
                )
            except:
                print(f"【Log】任务 {idx+1} 确认页检查失败。")
                pass

            print(f"【任务】任务 {idx+1} 成功。")
        except Exception as e:
            success = False
            print(f"【任务】任务 {idx+1} 失败。", type(e))
        finally:
            clear_handles(driver, handle)
    
    show_task_reward(driver)

    return success

def fetch_titles(driver):
    driver.get("https://zodgame.xyz/forum.php?mod=forumdisplay&fid=13")
    WebDriverWait(driver, 240).until(
        lambda x: x.title != "Just a moment..."
    )

    titles = []
    # Skip sticky threads (置顶/公告), only collect normal threads below "版块主题" separator
    xpath = '//tbody[starts-with(@id, "normalthread_")]//th//a[@class="s xst"]'
    elems = driver.find_elements(By.XPATH, xpath)
    for a in elems:
        title = a.get_attribute("textContent").strip()
        link = a.get_attribute("href")
        if title:
            titles.append((title, link))

    print(f"【爬取】共获取 {len(titles)} 条帖子标题。")
    return titles


def send_email(titles, email_user, email_pass):
    today = datetime.now().strftime("%Y-%m-%d")
    subject = f"ZodGame 帖子速递 - {today}"

    body_html = f'<h2>绅士游戏集散地 - {today} 帖子速递</h2><hr><ol>'
    for title, link in titles:
        body_html += f'<li><a href="{link}">{title}</a></li>'
    body_html += '</ol>'

    body_plain = f"绅士游戏集散地 - {today}\n{'-'*50}\n"
    for i, (title, link) in enumerate(titles, 1):
        body_plain += f"{i}. {title}\n   {link}\n"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email_user
    msg["To"] = email_user
    msg.attach(MIMEText(body_plain, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.163.com", 465) as server:
        server.login(email_user, email_pass)
        server.sendmail(email_user, email_user, msg.as_string())

    print(f"【邮件】已发送至 {email_user}。")


def zodgame(cookie_string, email_user=None, email_pass=None):
    options = uc.ChromeOptions()
    options.add_argument("--disable-popup-blocking")
    driver = uc.Chrome(driver_executable_path = """C:\SeleniumWebDrivers\ChromeDriver\chromedriver.exe""",
                       browser_executable_path = """C:\Program Files\Google\Chrome\Application\chrome.exe""",
                       options = options)

    # Load cookie
    driver.get("https://zodgame.xyz/")

    if cookie_string.startswith("cookie:"):
        cookie_string = cookie_string[len("cookie:"):]
    cookie_string = cookie_string.replace("/","%2")
    cookie_dict = [ 
        {"name" : x.split('=')[0].strip(), "value": x.split('=')[1].strip()} 
        for x in cookie_string.split(';')
    ]

    driver.delete_all_cookies()
    for cookie in cookie_dict:
        if cookie["name"] in ["qhMq_2132_saltkey", "qhMq_2132_auth"]:
            driver.add_cookie({
                "domain": "zodgame.xyz",
                "name": cookie["name"],
                "value": cookie["value"],
                "path": "/",
            })
    
    driver.get("https://zodgame.xyz/")
    
    WebDriverWait(driver, 240).until(
        lambda x: x.title != "Just a moment..."
    )
    assert len(driver.find_elements(By.XPATH, '//a[text()="用户名"]')) == 0, "Login fails. Please check your cookie."
        
    formhash = WebDriverWait(driver, 30).until(
        lambda x: x.find_element(By.XPATH, '//input[@name="formhash"]')
    ).get_attribute('value')
    assert zodgame_checkin(driver, formhash) and zodgame_task(driver, formhash), "Checkin failed or task failed."

    if email_user and email_pass:
        titles = fetch_titles(driver)
        send_email(titles, email_user, email_pass)

    driver.close()
    driver.quit()
    
if __name__ == "__main__":
    cookie_string = sys.argv[1]
    assert cookie_string

    email_user = sys.argv[2] if len(sys.argv) > 2 else None
    email_pass = sys.argv[3] if len(sys.argv) > 3 else None

    zodgame(cookie_string, email_user, email_pass)
