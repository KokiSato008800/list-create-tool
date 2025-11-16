from playwright.async_api import async_playwright
import asyncio
import random
import re
import os
import subprocess
import sys

class GoogleMapsScraper:
    """Googleマップスクレイピングクラス（安定性最優先）"""

    def __init__(self, start_rank=41, end_rank=200, min_wait=2.5, max_wait=4.5):
        self.start_rank = start_rank
        self.end_rank = end_rank
        self.min_wait = min_wait
        self.max_wait = max_wait

        # タイムアウト設定（段階的）
        self.TIMEOUT_PAGE_LOAD = 90000  # ページ読み込み: 90秒
        self.TIMEOUT_SEARCH = 60000     # 検索: 60秒
        self.TIMEOUT_ELEMENT = 30000    # 要素待機: 30秒
        self.TIMEOUT_CLICK = 20000      # クリック: 20秒

    async def random_wait(self):
        """ランダム待機（ブロック対策）"""
        wait_time = random.uniform(self.min_wait, self.max_wait)
        await asyncio.sleep(wait_time)

    async def scroll_to_load_results(self, page, target_count=200, log_callback=None):
        """結果リストをスクロールして読み込む"""
        if log_callback:
            log_callback(f"スクロールして{target_count}件の店舗を読み込み中...")

        try:
            # スクロール可能な要素を待機
            scrollable_element = await page.wait_for_selector(
                'div[role="feed"]',
                timeout=self.TIMEOUT_ELEMENT
            )

            if not scrollable_element:
                if log_callback:
                    log_callback("⚠️ スクロール要素が見つかりませんでした")
                return

            previous_count = 0
            no_change_count = 0
            max_no_change = 5

            while True:
                # 現在の店舗数を取得
                current_items = await page.query_selector_all('div[role="feed"] > div > div[jsaction]')
                current_count = len(current_items)

                if log_callback:
                    log_callback(f"現在の取得数: {current_count}件")

                # 目標件数に達したら終了
                if current_count >= target_count:
                    if log_callback:
                        log_callback(f"✓ 目標件数 {target_count}件に到達しました")
                    break

                # 件数が変わらない場合のチェック
                if current_count == previous_count:
                    no_change_count += 1
                    if no_change_count >= max_no_change:
                        if log_callback:
                            log_callback(f"⚠️ これ以上の読み込みができません。最終取得数: {current_count}件")
                        break
                else:
                    no_change_count = 0

                previous_count = current_count

                # スクロール実行
                await scrollable_element.evaluate("element => element.scrollBy(0, element.clientHeight * 0.8)")

                # ランダム待機
                await asyncio.sleep(random.uniform(1.0, 2.0))

        except Exception as e:
            if log_callback:
                log_callback(f"⚠️ スクロールエラー: {str(e)}")

    async def extract_place_details(self, page, place_element, rank, log_callback=None):
        """店舗詳細情報を取得（リトライ付き）"""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                # クリックして詳細を表示
                await place_element.click(timeout=self.TIMEOUT_CLICK)
                await self.random_wait()

                # 店舗名（必須）
                try:
                    name_element = await page.wait_for_selector('h1', timeout=self.TIMEOUT_ELEMENT)
                    name = await name_element.inner_text()
                except:
                    name = ""

                if not name:  # 店舗名がない場合はスキップ
                    if log_callback:
                        log_callback(f"  ⚠️ ランク{rank}: 店舗名取得失敗")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
                        continue
                    return None

                # カテゴリー
                try:
                    category_element = await page.query_selector('button[jsaction*="category"]')
                    category = await category_element.inner_text() if category_element else ""
                except:
                    category = ""

                # 評価
                try:
                    rating_element = await page.query_selector('div[jsaction*="rating"] span[aria-hidden="true"]')
                    rating_text = await rating_element.inner_text() if rating_element else ""
                    rating_match = re.search(r'(\d+\.\d+)', rating_text)
                    rating = rating_match.group(1) if rating_match else ""
                except:
                    rating = ""

                # レビュー数
                try:
                    review_element = await page.query_selector('div[jsaction*="rating"] span:nth-child(2) span[aria-label]')
                    review_count = ""
                    if review_element:
                        review_text = await review_element.get_attribute('aria-label')
                        review_match = re.search(r'([\d,]+)', review_text)
                        review_count = review_match.group(1).replace(',', '') if review_match else ""
                except:
                    review_count = ""

                # 住所
                try:
                    address_element = await page.query_selector('button[data-item-id="address"]')
                    address = ""
                    if address_element:
                        address_text = await address_element.inner_text()
                        address = address_text.split('\n')[-1] if '\n' in address_text else address_text
                except:
                    address = ""

                # 電話番号
                try:
                    phone_element = await page.query_selector('button[data-item-id*="phone"]')
                    phone = ""
                    if phone_element:
                        phone_text = await phone_element.inner_text()
                        phone = phone_text.split('\n')[-1] if '\n' in phone_text else phone_text
                except:
                    phone = ""

                # WebサイトURL
                try:
                    website_element = await page.query_selector('a[data-item-id="authority"]')
                    website = await website_element.get_attribute('href') if website_element else ""
                except:
                    website = ""

                # 営業時間
                try:
                    hours_button = await page.query_selector('button[data-item-id="oh"]')
                    hours = ""
                    if hours_button:
                        hours_text = await hours_button.get_attribute('aria-label')
                        hours = hours_text if hours_text else ""
                except:
                    hours = ""

                return {
                    '順位': rank,
                    '店舗名': name,
                    'カテゴリー': category,
                    '評価': rating,
                    'レビュー数': review_count,
                    '住所': address,
                    '電話番号': phone,
                    'WebサイトURL': website,
                    '営業時間': hours
                }

            except Exception as e:
                if attempt < max_retries - 1:
                    if log_callback:
                        log_callback(f"  ⚠️ ランク{rank}: エラー（{attempt + 1}/{max_retries}回目）、再試行中...")
                    await asyncio.sleep(2)
                else:
                    if log_callback:
                        log_callback(f"  ❌ ランク{rank}: 取得失敗 - {str(e)}")
                    return None

        return None

    @staticmethod
    def ensure_playwright_browsers():
        """Playwrightブラウザがインストールされているか確認し、なければインストール"""
        try:
            # chromium_pathが存在するか確認
            result = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                capture_output=True,
                text=True,
                timeout=300  # 5分のタイムアウト
            )
            if result.returncode != 0:
                print(f"Warning: Playwright install returned code {result.returncode}")
                print(f"stdout: {result.stdout}")
                print(f"stderr: {result.stderr}")
        except Exception as e:
            print(f"Warning: Could not install Playwright browsers: {e}")

    async def scrape_google_maps(self, keyword, start_rank=None, end_rank=None, log_callback=None):
        """Googleマップから店舗情報を取得"""
        # Playwrightブラウザを確保
        self.ensure_playwright_browsers()

        if start_rank is None:
            start_rank = self.start_rank
        if end_rank is None:
            end_rank = self.end_rank

        results = []

        async with async_playwright() as p:
            # ブラウザ起動
            browser = await p.chromium.launch(
                headless=True,  # ヘッドレスモード
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )

            # コンテキスト作成
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='ja-JP'
            )

            page = await context.new_page()
            page.set_default_timeout(self.TIMEOUT_ELEMENT)

            try:
                # Googleマップにアクセス（リトライ付き）
                if log_callback:
                    log_callback("Googleマップにアクセス中...")

                max_retries = 5
                for attempt in range(max_retries):
                    try:
                        await page.goto(
                            'https://www.google.com/maps',
                            wait_until='domcontentloaded',
                            timeout=self.TIMEOUT_PAGE_LOAD
                        )
                        if log_callback:
                            log_callback("✓ アクセス成功")
                        break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            if log_callback:
                                log_callback(f"⚠️ アクセス失敗（{attempt + 1}/{max_retries}回目）、5秒後に再試行...")
                            await asyncio.sleep(5)
                        else:
                            raise Exception(f"{max_retries}回試行しましたが接続できませんでした")

                await self.random_wait()

                # 検索ボックスに入力
                if log_callback:
                    log_callback(f"'{keyword}' を検索中...")

                search_box = await page.wait_for_selector('input#searchboxinput', timeout=self.TIMEOUT_SEARCH)
                await search_box.fill(keyword)
                await self.random_wait()

                # 検索実行
                await page.keyboard.press('Enter')
                await page.wait_for_timeout(5000)  # 検索結果の読み込み待機

                if log_callback:
                    log_callback("✓ 検索完了")

                # スクロールして結果を読み込み
                await self.scroll_to_load_results(page, end_rank, log_callback)

                # 全店舗要素を取得
                place_elements = await page.query_selector_all('div[role="feed"] > div > div[jsaction]')
                total_found = len(place_elements)

                if log_callback:
                    log_callback(f"\n取得可能な店舗数: {total_found}件")

                if total_found < start_rank:
                    if log_callback:
                        log_callback(f"⚠️ 開始順位({start_rank}位)より少ない店舗数です。このキーワードはスキップします。")
                    await browser.close()
                    return results

                # 指定範囲の店舗情報を取得
                target_elements = place_elements[start_rank-1:min(end_rank, total_found)]
                if log_callback:
                    log_callback(f"詳細情報を取得する店舗数: {len(target_elements)}件\n")

                for idx, place_element in enumerate(target_elements, start=start_rank):
                    if log_callback:
                        log_callback(f"[{idx}/{end_rank}] 店舗情報取得中...")

                    details = await self.extract_place_details(page, place_element, idx, log_callback)

                    if details:
                        details['検索キーワード'] = keyword
                        results.append(details)
                        if log_callback:
                            log_callback(f"  ✓ {details['店舗名']}")

                    # ブロック対策の待機
                    await self.random_wait()

                if log_callback:
                    log_callback(f"\n✓ {keyword}: {len(results)}件取得完了")

            except Exception as e:
                if log_callback:
                    log_callback(f"❌ エラー: {str(e)}")

            finally:
                await browser.close()

        return results
