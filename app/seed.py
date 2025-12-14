from app.database import get_database

def add_fake_data():
    # 1. Veritabanı Bağlantısını Çağır (Anahtarı al)
    db = get_database()
    
    if db is None:
        print(" Database connection failed!")
        return

    # 2. Koleksiyonu (Tabloyu) Seç
    # MongoDB'de tabloya 'Collection' denir. 
    # 'clients' adında bir kutu açıyoruz.
    clients_collection = db['clients']

    # 3. İngilizce Test Verisi Hazırla
    # Python'da buna 'Dictionary' (Sözlük) denir.
    fake_client = {
        "full_name": "John Doe",          # Ad Soyad -> full_name
        "phone": "+1 555 0199",           # Telefon -> phone
        "email": "johndoe@example.com",   # E-posta ekledik
        "gender": "Male",                 # Cinsiyet -> gender
        "notes": "Type 2 Diabetes patient. Needs low sugar diet." # Notlar -> notes
    }

    # 4. Veriyi Kutuya At (Insert)
    # insert_one: Tek bir kayıt ekler.
    clients_collection.insert_one(fake_client)
    
    print("SUCCESS: Dummy client 'John Doe' added to MongoDB!")

if __name__ == "__main__":
    add_fake_data()