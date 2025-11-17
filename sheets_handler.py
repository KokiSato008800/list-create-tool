import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

class SheetsHandler:
    """Google Sheets操作クラス"""

    def __init__(self, credentials_json, owner_email=None, target_folder_id=None):
        """
        Args:
            credentials_json (dict): サービスアカウントの認証情報（JSON形式）
            owner_email (str, optional): スプレッドシートの所有者に設定するメールアドレス
            target_folder_id (str, optional): スプレッドシートを保存するフォルダID
        """
        self.credentials_json = credentials_json
        self.owner_email = owner_email
        self.target_folder_id = target_folder_id
        self.client = None

    def authenticate(self):
        """Google Sheetsに認証"""
        if self.client is None:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]

            # google-auth を使用
            creds = Credentials.from_service_account_info(
                self.credentials_json,
                scopes=scope
            )
            self.client = gspread.authorize(creds)

        return self.client

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

        # 新しいスプレッドシート作成
        if self.target_folder_id:
            # 指定されたフォルダ内に作成
            spreadsheet = client.create(title, folder_id=self.target_folder_id)
        else:
            # デフォルト（ルートに作成）
            spreadsheet = client.create(title)

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

        # 共有設定
        try:
            # オーナーメールアドレスが指定されている場合は、そのユーザーに所有権を譲渡
            if self.owner_email:
                # まず編集者として追加
                spreadsheet.share(self.owner_email, perm_type='user', role='writer', notify=True,
                                 email_message='店舗リストの取得が完了しました。スプレッドシートをご確認ください。')
                # 所有権を譲渡（これによりサービスアカウントの容量を使わない）
                try:
                    spreadsheet.transfer_ownership(self.owner_email)
                except:
                    # 所有権譲渡に失敗した場合でも、編集者権限は付与されている
                    pass
            else:
                # オーナーが指定されていない場合は誰でも閲覧可能に設定
                spreadsheet.share('', perm_type='anyone', role='reader')
        except Exception as e:
            # 共有設定に失敗しても処理を続行
            print(f"Warning: Failed to share spreadsheet: {e}")
            pass

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
