# Google認証情報
# 本番環境ではStreamlit Secretsから読み込みます
# ローカル開発時は環境変数またはファイルから読み込んでください

import streamlit as st
import os
import json

def get_credentials():
    """認証情報を取得（Streamlit Secrets優先）"""

    # Streamlit Secretsから取得（本番環境）
    if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
        return st.secrets['gcp_service_account']

    # 環境変数から取得（ローカル開発）
    if 'GCP_SERVICE_ACCOUNT' in os.environ:
        return json.loads(os.environ['GCP_SERVICE_ACCOUNT'])

    # ファイルから取得（ローカル開発）
    credentials_file = 'credentials.json'
    if os.path.exists(credentials_file):
        with open(credentials_file, 'r') as f:
            return json.load(f)

    raise ValueError(
        "認証情報が見つかりません。\n"
        "Streamlit Cloudの場合: Secretsに 'gcp_service_account' を設定してください\n"
        "ローカルの場合: credentials.json ファイルを作成してください"
    )

def get_owner_email():
    """オーナーのメールアドレスを取得"""
    # Streamlit Secretsから取得
    if hasattr(st, 'secrets') and 'owner_email' in st.secrets:
        return st.secrets['owner_email']

    # 環境変数から取得
    if 'OWNER_EMAIL' in os.environ:
        return os.environ['OWNER_EMAIL']

    # デフォルト値（ローカル開発用）
    return None

# デフォルト設定
DEFAULT_START_RANK = 41
DEFAULT_END_RANK = 200
DEFAULT_MIN_WAIT = 2.5
DEFAULT_MAX_WAIT = 4.5

# タイムアウト設定（ミリ秒）
TIMEOUT_PAGE_LOAD = 90000  # ページ読み込み: 90秒
TIMEOUT_SEARCH = 60000     # 検索: 60秒
TIMEOUT_ELEMENT = 30000    # 要素待機: 30秒
TIMEOUT_CLICK = 20000      # クリック: 20秒
