# scraper.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import random
import re
import os
from utils import create_directory, extract_country_code
from fake_useragent import UserAgent

# Import selenium-wire webdriver
from seleniumwire import webdriver as SeleniumWireWebDriver # For proxy usage
from selenium import webdriver as StandardWebDriver # For no-proxy usage

def extract_brand_name(url):
    """从URL中提取品牌名称"""
    # 首先移除查询参数部分
    base_url = url.split('?')[0]
    
    # 从路径中提取域名部分
    domain = base_url.split('/')[-1]
    
    # 处理可能的subdomain前缀
    if domain.startswith('www.'):
        domain = domain[4:]
    
    # 根据不同的域名格式提取品牌名
    if domain.endswith('.com'):
        brand_name = domain.split('.')[0]
    elif '.co.' in domain:
        brand_name = domain.split('.')[0]
    else:
        parts = domain.split('.')
        if len(parts) > 1:
            brand_name = f"{parts[0]}_{parts[1]}"
        else:
            brand_name = parts[0]
    
    # 将提取的品牌名称转换为安全的文件名格式
    safe_brand_name = ''.join(c for c in brand_name if c.isalnum() or c in '_-.')
    
    return safe_brand_name

def get_random_headers():
    """生成随机的HTTP请求头"""
    try:
        # 锁死桌面 UA — Trustpilot 对移动端 UA 服务"snippet-only"DOM（无 country / rating / title / 完整 body）
        # fake_useragent 2.x 支持 platforms='pc'
        ua = UserAgent(platforms=['pc'])
        user_agent = ua.random
        # 兜底：万一仍命中移动 UA（库版本差异），强制走预定义列表
        if any(t in user_agent for t in ('iPhone', 'iPad', 'Android', 'Mobile')):
            raise ValueError("mobile UA leaked, fall through")
    except Exception:
        # 如果fake_useragent库不可用，使用预定义的UA列表
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/123.0.0.0 Safari/537.36",
        ]
        user_agent = random.choice(user_agents)
    
    # 构建随机语言偏好
    languages = ["en-US,en;q=0.9", "en-GB,en;q=0.9", "fr-FR,fr;q=0.8,en-US;q=0.6", 
                "zh-CN,zh;q=0.9,en;q=0.8", "de-DE,de;q=0.9,en;q=0.8", 
                "ja-JP,ja;q=0.9,en-US;q=0.8", "es-ES,es;q=0.9,en;q=0.8"]
    
    # 构建随机接受类型
    accept_types = [
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    ]
    
    # 构建随机接受编码
    accept_encodings = ["gzip, deflate, br", "gzip, deflate", "br, gzip, deflate"]
    
    headers = {
        "User-Agent": user_agent,
        "Accept": random.choice(accept_types),
        "Accept-Language": random.choice(languages),
        "Accept-Encoding": random.choice(accept_encodings),
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": random.choice(["max-age=0", "no-cache", "no-store"]),
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": random.choice(["none", "same-origin"]),
        "Sec-Fetch-User": "?1",
        "Pragma": random.choice(["no-cache", ""]),
    }
    
    return headers

def scrape_trustpilot_reviews(url, safe_brand_name, base_save_dir, thread_identifier="local_ip", selenium_wire_options=None, pages_to_scrape_for_test=None, start_page=1, end_page=None, cutoff_date=None):
    """从Trustpilot爬取评论. Now supports proxies via selenium-wire and saves to thread-specific subdir."""
    all_reviews = []
    all_page_files = []
    
    # Thread-specific save directory for pages
    pages_save_dir = os.path.join(base_save_dir, thread_identifier, "pages")
    create_directory(pages_save_dir) # create_directory is from utils.py
    
    print(f"[{thread_identifier}] 开始抓取 {safe_brand_name} 从 {url}. 保存到: {pages_save_dir}")
    if start_page > 1:
        print(f"[{thread_identifier}] 指定从第 {start_page} 页开始抓取")
    if end_page:
        print(f"[{thread_identifier}] 指定抓取到第 {end_page} 页结束")

    # 基本的Chrome选项配置
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--lang=en-US") # Attempt to standardize language
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # Initialize driver based on whether proxy options are provided
    driver = None
    current_headers = get_random_headers()
    chrome_options.add_argument(f"--user-agent={current_headers['User-Agent']}")
    # Note: For selenium-wire, other headers are not typically added via chrome_options like this.
    # They are part of the request interception if needed, or selenium-wire handles them with the proxy.

    if selenium_wire_options:
        print(f"[{thread_identifier}] 使用代理配置: {selenium_wire_options['proxy']['http']}")
        
        try:
            # 导入自定义的代理链模块
            from chain_proxy import create_seleniumwire_driver, verify_proxy_connection
            
            # 为selenium-wire准备Chrome选项
            wire_chrome_options = Options()
            wire_chrome_options.add_argument("--headless")
            wire_chrome_options.add_argument("--no-sandbox")
            wire_chrome_options.add_argument("--disable-dev-shm-usage")
            wire_chrome_options.add_argument("--disable-gpu")
            wire_chrome_options.add_argument("--window-size=1920,1080")
            wire_chrome_options.add_argument("--lang=en-US")
            wire_chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            wire_chrome_options.add_argument(f"--user-agent={current_headers['User-Agent']}")
            wire_chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            wire_chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 创建带有代理的WebDriver
            print(f"[{thread_identifier}] 正在创建带代理的WebDriver...")
            driver = create_seleniumwire_driver(selenium_wire_options, wire_chrome_options)
            
            if driver:
                # 验证代理连接
                if verify_proxy_connection(driver, thread_identifier):
                    print(f"[{thread_identifier}] 代理连接验证成功")
                else:
                    print(f"[{thread_identifier}] 警告: 代理连接验证失败，但将继续尝试抓取")
            else:
                # 回退到无代理模式
                print(f"[{thread_identifier}] 创建代理WebDriver失败，回退到使用本地IP模式...")
                driver = StandardWebDriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        except Exception as e:
            print(f"[{thread_identifier}] 代理设置失败: {e}")
            print(f"[{thread_identifier}] 回退到使用本地IP模式...")
            driver = StandardWebDriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    else:
        print(f"[{thread_identifier}] 使用本地IP (无代理)。")
        driver = StandardWebDriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    print(f"[{thread_identifier}] User-Agent: {current_headers['User-Agent'][:50]}...")
    
    base_url = url.split("?")[0]
    print(f"[{thread_identifier}] Base URL: {base_url}")
    
    pages_scraped_count = 0 # For the test limit

    try:
        first_page_url = f"{base_url}?languages=all&sort=recency" # languages=all for cross-region; sort=recency to get full review DOM (vs snippet preview) and chronological order
        driver.get(first_page_url)
        print(f"[{thread_identifier}] Accessed page 1: {first_page_url}")
        
        try:
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            ).click()
            print(f"[{thread_identifier}] Accepted cookies.")
        except:
            print(f"[{thread_identifier}] No cookie consent dialog found or failed to click.")
        
        # 如果开始页码大于1，我们只需直接跳到指定页码
        page_num = start_page if start_page > 0 else 1
        
        while True:
            # 检查是否超过了要抓取的测试页数
            if pages_to_scrape_for_test is not None and pages_scraped_count >= pages_to_scrape_for_test:
                print(f"[{thread_identifier}] Reached test page limit of {pages_to_scrape_for_test}. Stopping.")
                break
                
            # 检查是否超过了结束页码
            if end_page is not None and page_num > end_page:
                print(f"[{thread_identifier}] Reached specified end page {end_page}. Stopping.")
                break

            # 构建当前页面URL
            current_url_to_load = f"{base_url}?languages=all&sort=recency&page={page_num}" if page_num > 1 else first_page_url
            
            if page_num > 1 or start_page > 1: # 如果不是按顺序的第一页，需要显式导航
                print(f"[{thread_identifier}] Navigating to page {page_num}: {current_url_to_load}")
                delay = random.uniform(3, 8) # Shorter delay as an example
                print(f"[{thread_identifier}] Waiting {delay:.2f}s...")
                time.sleep(delay)
                driver.get(current_url_to_load)
                try: # Try to accept cookies again on new page load if dialog reappears
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))).click()
                except: pass
            
            if "404" in driver.title or "Whoops!" in driver.page_source or "Page not found" in driver.page_source:
                print(f"[{thread_identifier}] Page {page_num} appears to be 404 or end of reviews. Stopping.")
                break
            
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-service-review-card-paper='true']"))
                )
            except TimeoutException:
                print(f"[{thread_identifier}] Timeout waiting for reviews on page {page_num}. Checking for common end-of-reviews indicators.")
                if "no reviews matching your filter" in driver.page_source.lower() or \
                   "couldn't find any reviews" in driver.page_source.lower():
                    print(f"[{thread_identifier}] Found no reviews message. Stopping.")
                    break
                print(f"[{thread_identifier}] No clear end-of-reviews message, attempting to proceed or will stop if no reviews found.)")
                # Give it one more chance, then break if still no reviews
                time.sleep(5)
                if not driver.find_elements(By.CSS_SELECTOR, "article[data-service-review-card-paper='true']"):
                    print(f"[{thread_identifier}] Still no reviews found on page {page_num} after extra wait. Stopping.")
                    break
            except Exception:
                print(f"[{thread_identifier}] No clear end-of-reviews message, attempting to proceed or will stop if no reviews found.)")
                # Give it one more chance, then break if still no reviews
                time.sleep(5)
                if not driver.find_elements(By.CSS_SELECTOR, "article[data-service-review-card-paper='true']"):
                    print(f"[{thread_identifier}] Still no reviews found on page {page_num} after extra wait. Stopping.")
                    break
            
            time.sleep(random.uniform(2, 4)) # Page interaction delay
            
            review_containers = driver.find_elements(By.CSS_SELECTOR, "article[data-service-review-card-paper='true']")
            
            if not review_containers:
                print(f"[{thread_identifier}] No review containers found on page {page_num}. Stopping.")
                break
                
            print(f"[{thread_identifier}] Found {len(review_containers)} reviews on page {page_num}.")
            page_reviews = []
            
            for container in review_containers:
                try:
                    # Username — Trustpilot 2026 DOM: span[data-consumer-name-typography='true']
                    try:
                        username = container.find_element(
                            By.CSS_SELECTOR, "[data-consumer-name-typography='true']"
                        ).get_attribute("textContent").strip()
                    except NoSuchElementException:
                        username = "Unknown"

                    # Country — Trustpilot 2026 DOM has direct attribute (no more sibling-XPath gymnastics)
                    try:
                        country = container.find_element(
                            By.CSS_SELECTOR, "[data-consumer-country-typography='true']"
                        ).get_attribute("textContent").strip()
                        if not (country and len(country) == 2 and country.isupper()):
                            country = "Unknown"
                    except NoSuchElementException:
                        country = "Unknown"

                    # Date — ISO from <time datetime="...">
                    try:
                        review_date = container.find_element(
                            By.CSS_SELECTOR, "time[datetime]"
                        ).get_attribute("datetime").split("T")[0]
                    except NoSuchElementException:
                        review_date = "Unknown"

                    # Review title (new field)
                    try:
                        review_title = container.find_element(
                            By.CSS_SELECTOR, "[data-service-review-title-typography='true']"
                        ).get_attribute("textContent").strip()
                    except NoSuchElementException:
                        review_title = ""

                    # Review body — use textContent (not .text) to avoid lazy-render visibility quirks.
                    # Trustpilot has two layouts: full (data-service-review-text-typography) and snippet
                    # (data-relevant-review-text-typography, used for ~5 "featured" reviews per page even
                    # when sort=recency). Snippet is truncated with "See more" but still useful.
                    review_content = ""
                    for sel in ("[data-service-review-text-typography='true']",
                                "[data-relevant-review-text-typography='true']"):
                        try:
                            review_content = container.find_element(By.CSS_SELECTOR, sel).get_attribute("textContent").strip()
                            if review_content:
                                break
                        except NoSuchElementException:
                            continue

                    # Rating — direct attribute on div[data-service-review-rating]
                    try:
                        rating = container.find_element(
                            By.CSS_SELECTOR, "[data-service-review-rating]"
                        ).get_attribute("data-service-review-rating")
                    except NoSuchElementException:
                        rating = "Unknown"

                    review_data = {
                        'username': username,
                        'country': country,
                        'rating': rating,
                        'date': review_date,
                        'title': review_title,
                        'review': review_content,
                        'scraped_by': thread_identifier
                    }

                    page_reviews.append(review_data)
                    all_reviews.append(review_data)

                except Exception as e:
                    print(f"[{thread_identifier}] Error extracting review: {str(e)[:100]}...")
            
            if page_reviews:
                page_df = pd.DataFrame(page_reviews)
                page_file = os.path.join(pages_save_dir, f"{safe_brand_name}_reviews_page_{page_num}.csv")
                page_df.to_csv(page_file, index=False, encoding='utf-8-sig')
                print(f"[{thread_identifier}] Saved {len(page_reviews)} reviews from page {page_num} to {page_file}")
                all_page_files.append(page_file)
            
            pages_scraped_count += 1
            if len(page_reviews) == 0 and page_num > 1: # Stop if a non-first page has no reviews
                print(f"[{thread_identifier}] No reviews found on page {page_num} (and it's not the first page). Stopping.")
                break

            if cutoff_date and page_reviews:
                valid_dates = [r['date'] for r in page_reviews if r['date'] != "Unknown"]
                if valid_dates and min(valid_dates) < cutoff_date:
                    print(f"[{thread_identifier}] Reached cutoff_date {cutoff_date} on page {page_num} (oldest review on page: {min(valid_dates)}). Stopping.")
                    break

            page_num += 1
                
    except Exception as e:
        print(f"[{thread_identifier}] An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            try:
                driver.quit()
                print(f"[{thread_identifier}] WebDriver quit.")
            except Exception as e:
                print(f"[{thread_identifier}] Error quitting WebDriver: {e}")
    
    if all_reviews:
        all_reviews_df = pd.DataFrame(all_reviews)
        # Deduplication could be done here, or after merging all thread results in main.py
        print(f"[{thread_identifier}] Total reviews scraped by this thread: {len(all_reviews_df)}")
        return all_reviews_df, all_page_files # Return all page files from this thread
    else:
        print(f"[{thread_identifier}] No reviews scraped by this thread.")
        return pd.DataFrame(), []