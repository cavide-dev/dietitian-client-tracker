from PyQt5.QtWidgets import QMainWindow, QTableWidgetItem
from PyQt5.uic import loadUi
import os
# Veritabanı fonksiyonumuzu çağırıyoruz
from app.database import get_database

class MainController(QMainWindow):
    def __init__(self):
        super(MainController, self).__init__()
        
        # --- 1. ARAYÜZÜ YÜKLEME (UI Loading) ---
        # .ui dosyasının yolunu bulup yüklüyoruz.
        ui_path = os.path.join(os.path.dirname(__file__), '..', 'views', 'main_window.ui')
        try:
            loadUi(ui_path, self)
        except Exception as e:
            print(f"UI Loading Error: {e}")
            return

        # --- 2. VERİTABANI BAĞLANTISI ---
        # Uygulama açılır açılmaz veritabanı anahtarını cebimize koyuyoruz.
        self.db = get_database()

        # --- 3. BAŞLANGIÇ AYARLARI ---
        # Açılışta Dashboard sayfasını göster.
        self.stackedWidget.setCurrentWidget(self.page_dashboard)
        
        # Müşteri tablosunu doldur (Fonksiyonu aşağıda yazdık)
        self.load_clients_table()

        # --- 4. BUTON AKSİYONLARI (Signals & Slots) ---
        # lambda: Tek satırlık isimsiz fonksiyon demektir. Kısa yol.
        self.btn_dashboard.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.page_dashboard))
        self.btn_clients.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.page_clients))
        self.btn_diet_plans.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.page_diet_plans))
        self.btn_settings.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.page_settings))

    # --- ÖZEL FONKSİYONLAR ---

    def load_clients_table(self):
        """
        Veritabanından müşterileri çeker ve arayüzdeki tabloya yerleştirir.
        """
        # Eğer veritabanı bağlantısı yoksa işlem yapma, hata verir.
        if self.db is None:
            print("⚠️ No Database Connection!")
            return

        # 'clients' kutusunu (Collection) seç
        clients_collection = self.db['clients']
        
        # .find(): Kutudaki HER ŞEYİ getir.
        # list(): Gelen veriyi Python listesine çevir.
        all_clients = list(clients_collection.find())
        
        # Tabloyu Hazırla:
        # 1. Satır sayısını ayarla (Kaç müşteri varsa o kadar satır)
        self.tableWidget.setRowCount(len(all_clients))
        
        # 2. Sütun sayısını 3 yap (Ad, Telefon, Notlar)
        self.tableWidget.setColumnCount(3)
        
        # 3. Sütun Başlıklarını İngilizce Yap
        self.tableWidget.setHorizontalHeaderLabels(["Full Name", "Phone", "Notes"])

        # Döngü ile verileri tabloya yaz (Loop)
        # enumerate: Hem sırayı (row_index) hem veriyi (client) verir.
        for row_index, client in enumerate(all_clients):
            
            # --- 1. Sütun: İsim (Full Name) ---
            # client.get("full_name"): Veritabanından 'full_name' anahtarını al.
            # Yoksa "-" koy.
            name_value = client.get("full_name", "-")
            name_item = QTableWidgetItem(name_value) # Hücreye dönüşecek nesne
            self.tableWidget.setItem(row_index, 0, name_item) # 0. Sütuna koy
            
            # --- 2. Sütun: Telefon (Phone) ---
            phone_value = client.get("phone", "-")
            phone_item = QTableWidgetItem(phone_value)
            self.tableWidget.setItem(row_index, 1, phone_item) # 1. Sütuna koy
            
            # --- 3. Sütun: Notlar (Notes) ---
            notes_value = client.get("notes", "")
            note_item = QTableWidgetItem(notes_value)
            self.tableWidget.setItem(row_index, 2, note_item) # 2. Sütuna koy