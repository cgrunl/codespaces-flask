from flask import Flask, render_template, session, redirect, url_for, request, flash
import random
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# ----------------- UYGULAMA KURULUMU -----------------
app = Flask(__name__)
app.secret_key = 'cok-gizli-bir-anahtar-uretimde-kesinlikle-degisecek'
DATABASE = 'users.db'

# ----------------- VERİTABANI VE YARDIMCI FONKSİYONLAR -----------------

# Veritabanı bağlantısı oluşturan fonksiyon
def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row  # Sonuçlara sütun isimleriyle erişmemizi sağlar
    return db

# Veritabanını 'schema.sql' dosyasına göre ilk kez oluşturan fonksiyon
def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()
        print("Veritabanı başarıyla başlatıldı.")

# VIP seviyelerini veritabanına ilk kez ekleyen fonksiyon
def populate_vip_levels():
    with app.app_context():
        db = get_db()
        # INSERT OR IGNORE komutu, seviyeler zaten varsa tekrar eklemez.
        db.execute('INSERT OR IGNORE INTO vip_level (level, name, logo_url, min_balance, max_balance, commission_rate) VALUES (?, ?, ?, ?, ?, ?)',
                   (1, 'Amazon', '/static/images/amazon_logo.png', 20, 498, 4))
        db.execute('INSERT OR IGNORE INTO vip_level (level, name, logo_url, min_balance, max_balance, commission_rate) VALUES (?, ?, ?, ?, ?, ?)',
                   (2, 'Alibaba', '/static/images/alibaba_logo.png', 499, 899, 8))
        db.execute('INSERT OR IGNORE INTO vip_level (level, name, logo_url, min_balance, max_balance, commission_rate) VALUES (?, ?, ?, ?, ?, ?)',
                   (3, 'Aliexpress', '/static/images/aliexpress_logo.png', 899, 999999, 12))
        db.commit()
        print("VIP seviyeleri başarıyla eklendi.")

# Bir sayfanın sadece giriş yapmış kullanıcılar tarafından görülmesini sağlayan dekoratör
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Bu sayfayı görmek için giriş yapmalısınız.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ----------------- KULLANICI GİRİŞ/ÇIKIŞ VE KAYIT İŞLEMLERİ -----------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session: 
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM user WHERE username = ?', (username,)).fetchone()
        db.close()
        
        if user and check_password_hash(user['password'], password):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('home'))
        else:
            flash('Kullanıcı adı veya şifre yanlış!', 'error')

    return render_template("login.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session: 
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # .get() ile davet kodunu alıyoruz, boş olabilir. strip() ile boşlukları siliyoruz.
        referrer_code = request.form.get('invitation_code', '').strip()

        db = get_db()
        if db.execute('SELECT id FROM user WHERE username = ?', (username,)).fetchone():
            flash(f"'{username}' kullanıcı adı zaten alınmış!", 'error')
            db.close()
            return redirect(url_for('register'))

        referrer_id = None # Davet eden yoksa (isteğe bağlı olduğu için) ID boş (NULL) olacak
        
        # Sadece davet kodu girilmişse, bu kodun geçerli olup olmadığını kontrol et
        if referrer_code:
            referrer = db.execute('SELECT id FROM user WHERE invitation_code = ?', (referrer_code,)).fetchone()
            if not referrer:
                flash('Girilen davet kodu geçersiz!', 'error')
                db.close()
                return redirect(url_for('register'))
            referrer_id = referrer['id']

        # Her yeni kullanıcı için eşsiz bir davet kodu oluştur
        while True:
            new_invitation_code = str(random.randint(100000, 999999))
            if not db.execute('SELECT id FROM user WHERE invitation_code = ?', (new_invitation_code,)).fetchone():
                break
        
        hashed_password = generate_password_hash(password)
        
        db.execute(
            'INSERT INTO user (username, password, invitation_code, invited_by) VALUES (?, ?, ?, ?)',
            (username, hashed_password, new_invitation_code, referrer_id)
        )
        db.commit()
        db.close()
        
        flash('Kayıt başarılı! Lütfen şimdi giriş yapın.', 'success')
        return redirect(url_for('login'))
        
    return render_template("register.html")

@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('login'))

# ----------------- ANA NAVİGASYON SAYFALARI -----------------

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/home')
@login_required
def home():
    return render_template('home.html', active_page='home')

@app.route('/service')
@login_required
def service():
    return render_template('service.html', active_page='service')

@app.route('/menu')
@login_required
def menu():
    db = get_db()
    levels = db.execute('SELECT * FROM vip_level ORDER BY level').fetchall()
    db.close()
    return render_template('menu.html', active_page='menu', levels=levels)

@app.route('/tasks_record')
@login_required
def tasks_record():
    return render_template('tasks_record.html', active_page='record')

@app.route('/mine')
@login_required
def mine():
    db = get_db()
    user = db.execute('SELECT * FROM user WHERE id = ?', (session['user_id'],)).fetchone()
    db.close()
    return render_template('mine.html', active_page='mine', user=user)

# ----------------- ALT SAYFALAR (MINE SEKMESİ İÇİNDEKİLER VB.) -----------------

@app.route('/deposit')
@login_required
def deposit(): return render_template('deposit.html')

@app.route('/teams')
@login_required
def teams(): return render_template('teams.html')

@app.route('/wallet')
@login_required
def wallet(): return render_template('wallet.html')

@app.route('/invite')
@login_required
def invite():
    db = get_db()
    user = db.execute('SELECT invitation_code FROM user WHERE id = ?', (session['user_id'],)).fetchone()
    db.close()
    return render_template('invite.html', user=user)

@app.route('/profile')
@login_required
def profile(): return render_template('profile.html')

@app.route('/deposit_records')
@login_required
def deposit_records():
    # Bu veri ileride veritabanından gelecek, şimdilik statik
    records = [{'id': 'R2508211753221999350', 'status': 'initiate', 'timestamp': '2025-08-21 17:53:22', 'amount': 20.0}]
    return render_template('deposit_records.html', records=records)

@app.route('/withdrawal_records')
@login_required
def withdrawal_records():
    return render_template('withdrawal_records.html', records=[])

@app.route('/settings')
@login_required
def settings(): return render_template('settings.html')

@app.route('/task_detail/<int:level_id>')
@login_required
def task_detail(level_id):
    db = get_db()
    level = db.execute('SELECT * FROM vip_level WHERE level = ?', (level_id,)).fetchone()
    user = db.execute('SELECT balance FROM user WHERE id = ?', (session['user_id'],)).fetchone()
    db.close()
    return render_template('task_detail.html', level=level, user=user)


# ----------------- UYGULAMAYI ÇALIŞTIR -----------------
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)