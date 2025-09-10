import os
from app import db, populate_vip_levels, app

print("📡 PostgreSQL veritabanına bağlanılıyor...")

with app.app_context():
    # SQLAlchemy metadata ile tabloları oluştur
    db.create_all()
    print("✅ Tablolar oluşturuldu.")

    # VIP seviyeleri ekle
    print("⭐ VIP seviyeleri ekleniyor...")
    populate_vip_levels()
    print("✅ VIP seviyeleri eklendi.")

print("Kurulum tamamlandı! Artık uygulamayı başlatabilirsiniz.")
