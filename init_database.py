import os
from app import init_db, populate_vip_levels

# Eğer veritabanı dosyası varsa önce silerek temiz bir başlangıç yapalım.
if os.path.exists('users.db'):
    os.remove('users.db')
    print("'users.db' eski veritabanı dosyası silindi.")

print("Veritabanı ve tablolar oluşturuluyor...")
init_db() # Bu fonksiyon schema.sql'i çalıştırıp tabloları oluşturacak
print("--------------------")

print("VIP seviyeleri ekleniyor...")
populate_vip_levels() # Bu fonksiyon VIP verilerini ekleyecek
print("--------------------")

print("Kurulum tamamlandı! Artık 'python app.py' komutunu çalıştırabilirsiniz.")