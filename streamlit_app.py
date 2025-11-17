import streamlit as st
import asyncio
from datetime import datetime
import pandas as pd
from scraper import GoogleMapsScraper
from sheets_handler import SheetsHandler
from config import get_credentials, get_owner_email, get_target_folder_id, get_input_sheet_url, get_impersonate_email

# ページ設定
st.set_page_config(
    page_title="Googleマップ店舗情報取得ツール",
    page_icon="🗺️",
    layout="wide"
)

# タイトル
st.title("🗺️ Googleマップ店舗情報取得ツール")
st.markdown("---")

# 説明
st.markdown("""
### 使い方
1. 「データ取得開始」ボタンをクリックしてください
2. 処理完了後、新しいスプレッドシートにデータが保存されます

**⏱️ 予想実行時間**: 1キーワードあたり18〜20分

**📝 設定について**:
- 入力用スプレッドシート、取得範囲、保存先フォルダは全て設定済みです
- 入力用スプレッドシートで検索キーワードと取得範囲をカスタマイズできます
""")

st.markdown("---")

# 詳細設定（折りたたみ）- 開発者向け
with st.expander("⚙️ 詳細設定（通常は変更不要）"):
    col5, col6 = st.columns(2)

    with col5:
        min_wait = st.slider(
            "最小待機時間（秒）",
            1.0, 5.0, 2.5,
            help="各操作後の最小待機時間（ブロック対策）"
        )

    with col6:
        max_wait = st.slider(
            "最大待機時間（秒）",
            2.0, 10.0, 4.5,
            help="各操作後の最大待機時間（ブロック対策）"
        )

st.markdown("---")

# 実行ボタン
if st.button("🚀 データ取得開始", type="primary", use_container_width=True):
    # プログレス表示用のコンテナ
    progress_container = st.container()
    log_container = st.container()
    stats_container = st.container()

    with progress_container:
        st.info("🔄 処理を開始します...")
        overall_progress = st.progress(0)
        current_task = st.empty()

    with log_container:
        st.subheader("📋 処理ログ")
        log_area = st.empty()

    logs = []
    all_results = []

    try:
        # 設定を取得
        sheet_url = get_input_sheet_url()
        credentials = get_credentials()
        owner_email = get_owner_email()
        target_folder_id = get_target_folder_id()
        impersonate_email = get_impersonate_email()

        # Google Sheets接続
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Google Sheetsに接続中...")

        # Domain-Wide Delegationが有効な場合
        if impersonate_email:
            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔐 Domain-Wide Delegation有効")
            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] インパーソネート: {impersonate_email}")

        log_area.text_area("ログ", "\n".join(logs), height=300)

        sheets = SheetsHandler(
            credentials,
            owner_email=owner_email,
            target_folder_id=target_folder_id,
            impersonate_email=impersonate_email
        )
        keywords_data = sheets.get_search_keywords(sheet_url)

        total_keywords = len(keywords_data)
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ {total_keywords}件の検索キーワードを読み込みました")
        log_area.text_area("ログ", "\n".join(logs), height=300)

        # デフォルト設定を使用（スプレッドシート側で個別に指定可能）
        from config import DEFAULT_START_RANK, DEFAULT_END_RANK, DEFAULT_MIN_WAIT, DEFAULT_MAX_WAIT

        # スクレイピング実行
        scraper = GoogleMapsScraper(
            start_rank=DEFAULT_START_RANK,
            end_rank=DEFAULT_END_RANK,
            min_wait=min_wait,
            max_wait=max_wait
        )

        for idx, row in enumerate(keywords_data, 1):
            area = row.get('エリア', '')
            category = row.get('業種', '')
            keyword = f"{area} {category}"

            # カスタム範囲があれば使用、なければデフォルト
            custom_start = row.get('開始順位', DEFAULT_START_RANK)
            custom_end = row.get('終了順位', DEFAULT_END_RANK)

            # 進捗表示
            progress = idx / total_keywords
            overall_progress.progress(progress)
            current_task.markdown(f"**[{idx}/{total_keywords}] {keyword} を取得中...**")

            logs.append(f"\n[{datetime.now().strftime('%H:%M:%S')}] {'='*60}")
            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [{idx}/{total_keywords}] {keyword} の取得を開始")
            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 取得範囲: {custom_start}位 〜 {custom_end}位")
            log_area.text_area("ログ", "\n".join(logs[-50:]), height=300)  # 最新50行のみ表示

            # スクレイピング実行
            results = asyncio.run(scraper.scrape_google_maps(
                keyword,
                custom_start,
                custom_end,
                lambda msg: logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}") or log_area.text_area("ログ", "\n".join(logs[-50:]), height=300)
            ))

            all_results.extend(results)
            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ {keyword}: {len(results)}件取得完了")
            log_area.text_area("ログ", "\n".join(logs[-50:]), height=300)

            # 次のキーワードまで待機
            if idx < total_keywords:
                import random
                wait_time = random.uniform(5, 10)
                logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 次の検索まで {wait_time:.1f}秒 待機中...")
                log_area.text_area("ログ", "\n".join(logs[-50:]), height=300)
                import time
                time.sleep(wait_time)

        # 完了
        overall_progress.progress(1.0)
        current_task.markdown("**✅ 全てのキーワードの取得が完了しました**")

        logs.append(f"\n[{datetime.now().strftime('%H:%M:%S')}] {'='*60}")
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 全キーワードの取得完了")
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 総取得件数: {len(all_results)}件")
        log_area.text_area("ログ", "\n".join(logs[-50:]), height=300)

        # 統計表示
        with stats_container:
            st.subheader("📊 取得統計")
            col_stat1, col_stat2, col_stat3 = st.columns(3)

            with col_stat1:
                st.metric("検索キーワード数", f"{total_keywords}件")

            with col_stat2:
                st.metric("総取得件数", f"{len(all_results)}件")

            with col_stat3:
                avg_per_keyword = len(all_results) / total_keywords if total_keywords > 0 else 0
                st.metric("1キーワードあたり平均", f"{avg_per_keyword:.1f}件")

        # スプレッドシートに保存
        if all_results:
            logs.append(f"\n[{datetime.now().strftime('%H:%M:%S')}] 新しいスプレッドシートに保存中...")
            log_area.text_area("ログ", "\n".join(logs[-50:]), height=300)

            spreadsheet_id = sheets.save_to_new_spreadsheet(all_results)
            spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ 保存完了")
            log_area.text_area("ログ", "\n".join(logs[-50:]), height=300)

            st.success(f"✅ 処理が完了しました！{len(all_results)}件のデータを取得しました。")
            st.markdown(f"### 📄 結果スプレッドシート")
            st.markdown(f"[スプレッドシートを開く]({spreadsheet_url})")

            # プレビュー表示
            with st.expander("📋 取得データのプレビュー（最初の10件）"):
                df = pd.DataFrame(all_results[:10])
                st.dataframe(df, use_container_width=True)
        else:
            st.warning("⚠️ データを取得できませんでした")

    except Exception as e:
        st.error(f"❌ エラーが発生しました: {str(e)}")
        logs.append(f"\n[{datetime.now().strftime('%H:%M:%S')}] ❌ エラー: {str(e)}")
        log_area.text_area("ログ", "\n".join(logs[-50:]), height=300)

        import traceback
        with st.expander("🔍 詳細なエラー情報"):
            st.code(traceback.format_exc())

# サイドバー
with st.sidebar:
    st.header("ℹ️ 情報")

    st.markdown("""
    ### このツールについて
    Googleマップから店舗情報を自動取得し、Googleスプレッドシートに保存します。

    ### 取得する情報
    - 店舗名
    - カテゴリー
    - 評価（星）
    - レビュー数
    - 住所
    - 電話番号
    - WebサイトURL
    - 営業時間

    ### 注意事項
    - 実行には時間がかかります（1キーワード18〜20分）
    - ブラウザを閉じないでください
    - Googleマップからブロックされる可能性があります

    ### サポート
    問題が発生した場合は、ログを確認してください。
    """)

    st.markdown("---")
    st.markdown("### 🔧 技術情報")
    st.code(f"""
Python: 3.8+
Streamlit: 最新版
Playwright: 最新版
    """)
