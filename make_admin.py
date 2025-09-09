import sys
from app import app, db, User

# Komut satırından bir kullanıcı adı girilip girilmediğini kontrol et
if len(sys.argv) < 2:
    print("\nLütfen bir kullanıcı adı belirtin.")
    print("Kullanım: python make_admin.py <kullanici_adi>\n")
    sys.exit(1) # Script'i sonlandır

username_to_admin = sys.argv[1]

# Veritabanı işlemleri için uygulama bağlamını kullan
with app.app_context():
    # Belirtilen kullanıcı adını veritabanında ara
    user = User.query.filter_by(username=username_to_admin).first()

    # Kullanıcı bulunduysa admin yap
    if user:
        user.is_admin = True
        db.session.commit()
        print(f"\n✅ BAŞARI: '{user.username}' kullanıcısı artık bir admin.\n")
    # Kullanıcı bulunamadıysa hata ver
    else:
        print(f"\n❌ HATA: '{username_to_admin}' adında bir kullanıcı bulunamadı.\n")