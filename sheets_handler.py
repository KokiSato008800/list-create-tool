import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

class SheetsHandler:
    """Google Sheets操作クラス"""

    def __init__(self, credentials_json, owner_email=None, target_folder_id=None, impersonate_email=None):
        """
        Args:
            credentials_json (dict): サービスアカウントの認証情報（JSON形式）
            owner_email (str, optional): スプレッドシートの所有者に設定するメールアドレス（非推奨、Domain-Wide Delegationを使用してください）
            target_folder_id (str, optional): スプレッドシートを保存するフォルダID
            impersonate_email (str, optional): インパーソネートするユーザーのメールアドレス（Domain-Wide Delegation用）
        """
        self.credentials_json = credentials_json
        self.owner_email = owner_email
        self.target_folder_id = target_folder_id
        self.impersonate_email = impersonate_email
        self.client = None
        self.credentials = None  # 認証情報を保存
        self.drive_service = None  # Drive APIサービスを保存

    def authenticate(self):
        """Google Sheetsに認証（Domain-Wide Delegation対応）"""
        if self.client is None:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]

            # サービスアカウントの認証情報を作成
            self.credentials = Credentials.from_service_account_info(
                self.credentials_json,
                scopes=scope
            )

            # Domain-Wide Delegationが有効な場合、ユーザーをインパーソネート
            if self.impersonate_email:
                print(f"🔐 Domain-Wide Delegation有効: {self.impersonate_email} としてアクセス")
                self.credentials = self.credentials.with_subject(self.impersonate_email)

            self.client = gspread.authorize(self.credentials)

        return self.client

    def _get_drive_service(self):
        """Drive APIサービスを取得"""
        if self.drive_service is None:
            from googleapiclient.discovery import build

            # 認証情報が未作成の場合は作成
            if self.credentials is None:
                self.authenticate()

            self.drive_service = build('drive', 'v3', credentials=self.credentials)

        return self.drive_service

    def get_search_keywords(self, sheet_url):
        """
        入力シートから検索キーワードを取得

        Args:
            sheet_url (str): スプレッドシートのURL

        Returns:
            list: 検索キーワードのリスト（辞書形式）
        """
        client = self.authenticate()
        sheet = client.open_by_url(sheet_url).sheet1
        data = sheet.get_all_records()
        return data

    def save_to_new_spreadsheet(self, data, title=None):
        """
        取得データを新しいGoogleスプレッドシートに保存
        Domain-Wide Delegationを使用している場合、ファイルはインパーソネートされたユーザーの所有になります

        Args:
            data (list): 保存するデータ（辞書のリスト）
            title (str, optional): スプレッドシートのタイトル

        Returns:
            str: 作成したスプレッドシートのID
        """
        if not data:
            raise ValueError("保存するデータがありません")

        client = self.authenticate()

        # タイトル生成
        if not title:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            title = f'店舗リスト_{timestamp}'

        # フォルダIDが指定されている場合は、Drive APIを使用してフォルダ内に作成
        if self.target_folder_id:
            drive_service = self._get_drive_service()

            # スプレッドシートのメタデータ
            file_metadata = {
                'name': title,
                'mimeType': 'application/vnd.google-apps.spreadsheet',
                'parents': [self.target_folder_id]
            }

            # 空のスプレッドシートを作成
            # Domain-Wide Delegationが有効な場合、ファイルの所有者はインパーソネートされたユーザーになる
            file = drive_service.files().create(
                body=file_metadata,
                fields='id',
                supportsAllDrives=True  # Shared Driveサポート（必要に応じて）
            ).execute()

            spreadsheet_id = file.get('id')
            spreadsheet = client.open_by_key(spreadsheet_id)

            if self.impersonate_email:
                print(f"✅ スプレッドシートを作成: {title}")
                print(f"   所有者: {self.impersonate_email}")
                print(f"   保存先フォルダ: {self.target_folder_id}")
        else:
            # デフォルト（ルートに作成）
            # Domain-Wide Delegationが有効な場合、ファイルの所有者はインパーソネートされたユーザーになる
            spreadsheet = client.create(title)

            if self.impersonate_email:
                print(f"✅ スプレッドシートを作成: {title}")
                print(f"   所有者: {self.impersonate_email}")

        worksheet = spreadsheet.sheet1

        # DataFrameに変換
        df = pd.DataFrame(data)

        # カラムの順序を整理
        column_order = [
            '検索キーワード',
            '順位',
            '店舗名',
            'カテゴリー',
            '評価',
            'レビュー数',
            '住所',
            '電話番号',
            'WebサイトURL',
            '営業時間'
        ]

        # 存在するカラムのみ選択
        existing_columns = [col for col in column_order if col in df.columns]
        df = df[existing_columns]

        # スプレッドシートに書き込み
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())

        # 共有設定（Domain-Wide Delegationを使用している場合は所有権譲渡は不要）
        if not self.impersonate_email:
            # Domain-Wide Delegationが無効な場合のみ、従来の共有設定を使用（非推奨）
            try:
                if self.owner_email:
                    # まず編集者として追加
                    spreadsheet.share(self.owner_email, perm_type='user', role='writer', notify=True,
                                     email_message='店舗リストの取得が完了しました。スプレッドシートをご確認ください。')
                    # 所有権を譲渡（ほとんどの場合失敗する）
                    try:
                        spreadsheet.transfer_ownership(self.owner_email)
                        print(f"✅ 所有権を譲渡: {self.owner_email}")
                    except Exception as transfer_error:
                        # 所有権譲渡に失敗（ドメインが異なる場合は必ず失敗する）
                        print(f"⚠️ 所有権譲渡に失敗しました: {transfer_error}")
                        print(f"⚠️ ファイルはサービスアカウントの所有のままです")
                else:
                    # オーナーが指定されていない場合は誰でも閲覧可能に設定
                    spreadsheet.share('', perm_type='anyone', role='reader')
            except Exception as e:
                # 共有設定に失敗しても処理を続行
                print(f"⚠️ 共有設定に失敗: {e}")
        else:
            # Domain-Wide Delegationが有効な場合
            # ファイルは既にインパーソネートされたユーザーの所有なので、所有権譲渡は不要
            print(f"ℹ️ Domain-Wide Delegation有効のため、所有権譲渡はスキップします")

        return spreadsheet.id

    def append_to_existing_sheet(self, sheet_url, data):
        """
        既存のスプレッドシートにデータを追加

        Args:
            sheet_url (str): スプレッドシートのURL
            data (list): 追加するデータ（辞書のリスト）
        """
        if not data:
            raise ValueError("追加するデータがありません")

        client = self.authenticate()
        sheet = client.open_by_url(sheet_url).sheet1

        # DataFrameに変換
        df = pd.DataFrame(data)

        # データを追加
        for _, row in df.iterrows():
            sheet.append_row(row.tolist())

    def create_template_sheet(self, title="店舗リスト入力テンプレート"):
        """
        入力用のテンプレートシートを作成

        Args:
            title (str): スプレッドシートのタイトル

        Returns:
            str: 作成したスプレッドシートのID
        """
        client = self.authenticate()

        # 新しいスプレッドシート作成
        spreadsheet = client.create(title)
        worksheet = spreadsheet.sheet1

        # ヘッダー行を設定
        headers = ['エリア', '業種', '開始順位', '終了順位']
        worksheet.update([headers])

        # サンプルデータを追加
        sample_data = [
            ['京都', '居酒屋', 41, 200],
            ['京都', '焼肉', 41, 200],
            ['京都', '海鮮', 41, 200],
            ['金沢', '居酒屋', 41, 200],
            ['金沢', '焼肉', 41, 200],
            ['金沢', '海鮮', 41, 200],
            ['博多', '居酒屋', 41, 200],
            ['博多', '焼肉', 41, 200]
        ]

        for row in sample_data:
            worksheet.append_row(row)

        # 共有設定
        try:
            spreadsheet.share('', perm_type='anyone', role='writer')
        except:
            pass

        return spreadsheet.id
