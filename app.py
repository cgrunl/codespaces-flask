import os
import random
import string
import base64
import io
from functools import wraps
from flask import Flask, render_template, session, redirect, url_for, request, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_admin.actions import action
from flask_babel import Babel
from PIL import Image, ImageDraw, ImageFont
from wtforms import PasswordField

# ----------------- UYGULAMA KURULUMU -----------------
app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

app = Flask(__name__)
app.secret_key = os.urandom(24)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL").replace("postgresql://", "postgresql+psycopg2://")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

db = SQLAlchemy(app)
babel = Babel(app)

# ----------------- VERİTABANI MODELLERİ (YENİ ÖZELLİKLER EKLENDİ) -----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    invitation_code = db.Column(db.String(20), unique=True, nullable=False)
    invited_by = db.Column(db.Integer, nullable=True)
    balance = db.Column(db.Float, default=0.0, nullable=False)
    vip_level = db.Column(db.Integer, default=1, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    has_completed_any_vip = db.Column(db.Boolean, default=False, nullable=False) # Para çekme kilidi için
    checkpoint_target = db.Column(db.Float, default=0.0, nullable=False) # Görev kontrol noktası için
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f"<User {self.username}>"

class VipLevel(db.Model):
    __tablename__ = 'vip_level'
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    logo_url = db.Column(db.String(200))
    min_balance = db.Column(db.Float, nullable=False)
    max_tasks = db.Column(db.Integer, default=25, nullable=False) # Görev limiti için
    commission_rate = db.Column(db.Float, nullable=False)
    max_balance = db.Column(db.Float, default=0.0, nullable=False)


    def __repr__(self):
        return f"<VipLevel {self.level} - {self.name}>"

class UserTaskProgress(db.Model):
    __tablename__ = 'user_task_progress'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vip_level = db.Column(db.Integer, nullable=False)
    tasks_completed = db.Column(db.Integer, default=0, nullable=False)
    user = db.relationship('User', backref=db.backref('task_progress', lazy=True))

class TransactionLog(db.Model):
    __tablename__ = 'transaction_log'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    user = db.relationship('User', backref=db.backref('transactions', lazy=True))

    def __repr__(self):
        return f"<Tx {self.id} {self.type} {self.amount} {self.status}>"

class Wallet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    protocol = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    user = db.relationship('User', backref=db.backref('wallets', lazy=True))

    def __repr__(self):
        return f"<Wallet {self.name} ({self.protocol})>"

# ----------------- ADMIN PANELİ (GELİŞMİŞ VE DÜZELTİLMİŞ) -----------------
class ProtectedAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return session.get('is_admin', False)
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

class ProtectedModelView(ModelView):
    can_view_details = True
    can_export = True
    page_size = 50

    def is_accessible(self):
        return session.get('is_admin', False)
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

class UserAdminView(ProtectedModelView):
    column_searchable_list = ['username', 'invitation_code']
    column_filters = ['is_admin', 'vip_level', 'created_at']
    column_editable_list = ['balance', 'vip_level', 'is_admin']
    column_list = ['id', 'username', 'balance', 'vip_level', 'is_admin', 'has_completed_any_vip', 'checkpoint_target', 'created_at']
    column_sortable_list = ['id', 'username', 'balance', 'vip_level', 'created_at']
    form_columns = ['username', 'balance', 'vip_level', 'is_admin', 'has_completed_any_vip', 'checkpoint_target', 'new_password']

    form_extra_fields = {
        'new_password': PasswordField('Yeni Şifre (Boş bırakırsanız değişmez)')
    }
    
    def on_model_change(self, form, model, is_created):
        if 'new_password' in form and form.new_password.data:
            model.password = generate_password_hash(form.new_password.data)
        elif is_created and not model.password:
            model.password = generate_password_hash("ChangeMe123!")

class VipLevelAdminView(ProtectedModelView):
    column_list = ['id', 'level', 'name', 'min_balance', 'max_tasks', 'commission_rate']
    column_editable_list = ['name', 'min_balance', 'max_tasks', 'commission_rate']
    form_columns = ['level', 'name', 'logo_url', 'min_balance', 'max_tasks', 'commission_rate']

class TransactionAdminView(ProtectedModelView):
    column_list = ['id', 'user', 'type', 'amount', 'status', 'timestamp']
    column_filters = ['type', 'status', 'timestamp']
    column_searchable_list = ['user.username']
    can_edit = True
    can_create = False
    can_delete = False
    form_columns = ['status']
    
    @action('approve', 'Seçilenleri Onayla', 'Onaylamak istediğinize emin misiniz?')
    def action_approve(self, ids):
        query = TransactionLog.query.filter(TransactionLog.id.in_(ids))
        count = 0
        for transaction in query.all():
            if transaction.status == 'pending':
                if transaction.type == 'deposit':
                    user = db.session.get(User, transaction.user_id)
                    if user:
                        user.balance += transaction.amount
                        if user.checkpoint_target > 0 and user.balance >= user.checkpoint_target:
                            user.checkpoint_target = 0.0
                        check_and_upgrade_vip(user)
                transaction.status = 'completed'
                count += 1
        db.session.commit()
        flash(f"{count} işlem onaylandı.", 'success')

    @action('reject', 'Seçilenleri Reddet', 'Reddetmek istediğinize emin misiniz?')
    def action_reject(self, ids):
        query = TransactionLog.query.filter(TransactionLog.id.in_(ids))
        count = 0
        for transaction in query.all():
            if transaction.status == 'pending':
                if transaction.type == 'withdrawal':
                    user = db.session.get(User, transaction.user_id)
                    if user:
                        user.balance += transaction.amount
                transaction.status = 'rejected'
                count += 1
        db.session.commit()
        flash(f"{count} işlem reddedildi.", 'success')

class WalletAdminView(ProtectedModelView):
    column_list = ['id', 'user', 'name', 'protocol', 'address']
    column_searchable_list = ['name', 'protocol', 'address']
    form_columns = ['user', 'name', 'protocol', 'address']

admin = Admin(app, name='Proje Admin', template_mode='bootstrap3', index_view=ProtectedAdminIndexView())
admin.add_view(UserAdminView(User, db.session, name="Kullanıcılar"))
admin.add_view(VipLevelAdminView(VipLevel, db.session, name="VIP Seviyeleri"))
admin.add_view(TransactionAdminView(TransactionLog, db.session, name="İşlemler"))
admin.add_view(WalletAdminView(Wallet, db.session, name="Cüzdanlar"))
admin.add_view(ProtectedModelView(UserTaskProgress, db.session, name="Görev İlerlemesi"))

# ----------------- YARDIMCI FONKSİYONLAR -----------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_random_notification():
    users = ["m****7", "R****3", "a****9", "k****1", "s****5"]
    amount = f"{random.uniform(5.0, 150.0):.2f}"
    return {"user": random.choice(users), "amount": amount}

def check_and_upgrade_vip(user):
    if not user:
        return
    highest_level = db.session.query(db.func.max(VipLevel.level)).scalar()
    if not highest_level or user.vip_level >= highest_level:
        return
    next_level_vip = user.vip_level + 1
    required_level = VipLevel.query.filter_by(level=next_level_vip).first()
    if required_level and user.balance >= required_level.min_balance:
        user.vip_level = next_level_vip
        db.session.commit()

def generate_captcha():
    text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    session['captcha'] = text
    img = Image.new('RGB', (150, 50), color=(240, 240, 240))
    d = ImageDraw.Draw(img)
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/Library/Fonts/Arial Bold.ttf"
    ]
    font = None
    for path in font_paths:
        try:
            font = ImageFont.truetype(path, 32)
            break
        except Exception:
            continue
    if font:
        d.text((25, 8), text, fill=(50, 50, 50), font=font)
    else:
        d.text((10, 10), text, fill=(50, 50, 50))
    for _ in range(160):
        d.point((random.randint(0, 150), random.randint(0, 50)), fill=(150, 150, 150))
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

# ----------------- DİL DESTEĞİ -----------------
LANGUAGES = [ {'code': 'en', 'flag': 'us', 'name': 'English'}, {'code': 'tr', 'flag': 'tr', 'name': 'Türkçe'} ]
translations = {
    'en': { "welcome": "Welcome!", "signin_prompt": "Sign in to your account", "username_placeholder": "Username", "password_placeholder": "Password", "security_code_placeholder": "Verification Code", "signin_button": "Sign In", "no_account_prompt": "Don't have an account?", "signup_link": "Sign Up", "setting": "Setting", "language_settings": "Language settings", "select_language": "Please select a language"},
    'tr': { "welcome": "Hoş Geldiniz!", "signin_prompt": "Hesabınıza giriş yapın", "username_placeholder": "Kullanıcı Adı", "password_placeholder": "Şifre", "security_code_placeholder": "Doğrulama Kodu", "signin_button": "Giriş Yap", "no_account_prompt": "Hesabınız yok mu?", "signup_link": "Kayıt Ol", "setting": "Ayarlar", "language_settings": "Dil ayarları", "select_language": "Lütfen bir dil seçin"}
}
@app.context_processor
def inject_global_vars():
    lang_code = session.get('language', 'en')
    selected_translations = translations.get(lang_code, translations['en']).copy()
    for key in translations['en']:
        if key not in selected_translations:
            selected_translations[key] = translations['en'][key]
    return dict(languages=LANGUAGES, lang=lang_code, text=selected_translations)

# ----------------- ROTALAR (ROUTES) -----------------
@app.route('/set_language/<lang>')
def set_language(lang):
    if lang in [l['code'] for l in LANGUAGES]:
        session['language'] = lang
    return redirect(request.referrer or url_for('index'))

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        captcha_input = request.form.get('captcha', '')
        if 'captcha' not in session or captcha_input.upper() != session.get('captcha', ' ').upper():
            flash("Güvenlik kodu yanlış!", 'error')
            return redirect(url_for('login'))
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session.clear()
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            if user.is_admin:
                return redirect(url_for('admin.index'))
            return redirect(url_for('home'))
        else:
            flash('Kullanıcı adı veya şifre yanlış!', 'error')
    captcha_image = generate_captcha()
    return render_template("login.html", captcha_image=captcha_image)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        referrer_code = request.form.get('invitation_code', '').strip()
        if not username or not password:
            flash("Kullanıcı adı ve şifre boş olamaz.", "error")
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash(f"'{username}' kullanıcı adı zaten alınmış!", 'error')
            return redirect(url_for('register'))
        referrer_id = None
        if referrer_code:
            referrer = User.query.filter_by(invitation_code=referrer_code).first()
            if not referrer:
                flash('Girilen davet kodu geçersiz!', 'error')
                return redirect(url_for('register'))
            referrer_id = referrer.id
        while True:
            new_invitation_code = ''.join(random.choices(string.digits, k=6))
            if not User.query.filter_by(invitation_code=new_invitation_code).first():
                break
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password, invitation_code=new_invitation_code, invited_by=referrer_id)
        db.session.add(new_user)
        db.session.commit()
        flash('Kayıt başarılı! Lütfen şimdi giriş yapın.', 'success')
        return redirect(url_for('login'))
    return render_template("register.html")

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash("Başarıyla çıkış yaptınız.", "success")
    return redirect(url_for('login'))

@app.route('/home')
@login_required
def home():
    notification = get_random_notification()
    user = db.session.get(User, session['user_id'])
    return render_template('home.html', active_page='home', notification=notification, user=user)

@app.route('/service')
@login_required
def service():
    return render_template('service.html', active_page='service')

@app.route('/menu')
@login_required
def menu():
    levels = VipLevel.query.order_by(VipLevel.level).all()
    user = db.session.get(User, session['user_id'])
    return render_template('menu.html', active_page='menu', levels=levels, user=user)

@app.route('/tasks_record')
@login_required
def tasks_record():
    records = TransactionLog.query.filter_by(user_id=session['user_id'], type='commission').order_by(TransactionLog.timestamp.desc()).all()
    return render_template('tasks_record.html', records=records, active_page='record')

@app.route('/mine')
@login_required
def mine():
    user = db.session.get(User, session['user_id'])
    return render_template('mine.html', active_page='mine', user=user)

@app.route('/deposit', methods=['GET', 'POST'])
@login_required
def deposit():
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount', 0))
        except (ValueError, TypeError):
            flash("Geçersiz miktar girdiniz.", "error")
            return redirect(url_for('deposit'))
        if amount < 5.0:
            flash("Yatırma miktarı en az 5 USDT olmalıdır.", "error")
            return redirect(url_for('deposit'))
        new_transaction = TransactionLog(user_id=session['user_id'], type='deposit', amount=amount, status='pending')
        db.session.add(new_transaction)
        db.session.commit()
        return redirect(url_for('deposit_details', transaction_id=new_transaction.id))
    return render_template('deposit.html')

@app.route('/deposit_details/<int:transaction_id>')
@login_required
def deposit_details(transaction_id):
    transaction = TransactionLog.query.filter_by(id=transaction_id, user_id=session['user_id']).first_or_404()
    wallet_address = "TMbqptDJg3tXYtGq5b6yMMLZQ79Yz8ggxP"
    return render_template('deposit_details.html', transaction=transaction, wallet_address=wallet_address)

@app.route('/grab_order', methods=['POST'])
@login_required
def grab_order():
    level_id = int(request.form.get('level_id', 0))
    user = db.session.get(User, session['user_id'])
    level = VipLevel.query.filter_by(level=level_id).first_or_404()

    if user.checkpoint_target > 0 and user.balance < user.checkpoint_target:
        needed = user.checkpoint_target - user.balance
        return jsonify({'success': False, 'message': f"Devam etmek için {needed:.2f} USDT daha yatırmanız gerekli."})
    
    if user.checkpoint_target > 0 and user.balance >= user.checkpoint_target:
        user.checkpoint_target = 0.0

    progress = UserTaskProgress.query.filter_by(user_id=user.id, vip_level=level_id).first()
    if not progress:
        progress = UserTaskProgress(user_id=user.id, vip_level=level_id, tasks_completed=0)
        db.session.add(progress)
    
    if progress.tasks_completed >= level.max_tasks:
        return jsonify({'success': False, 'message': 'Bu VIP seviyesi için tüm görevlerinizi tamamladınız.'})
    
    if user.balance < level.min_balance:
        return jsonify({'success': False, 'message': 'Bu işlem için bakiyeniz yetersiz.'})
    
    commission_earned = user.balance * (level.commission_rate / 100.0)
    user.balance += commission_earned
    progress.tasks_completed += 1
    
    if progress.tasks_completed in [10, 20]:
        user.checkpoint_target = user.balance * 1.80

    if progress.tasks_completed >= level.max_tasks:
        user.has_completed_any_vip = True

    new_log = TransactionLog(user_id=user.id, type='commission', amount=commission_earned, status='completed')
    db.session.add(new_log)
    db.session.commit()
    check_and_upgrade_vip(user)
    
    return jsonify({
        'success': True, 
        'message': f'Tebrikler! {commission_earned:.2f} USDT komisyon kazandınız.',
        'new_balance': f'{user.balance:.2f}',
        'tasks_completed': progress.tasks_completed
    })

@app.route('/teams')
@login_required
def teams():
    team_members = User.query.filter_by(invited_by=session['user_id']).all()
    return render_template('teams.html', team_members=team_members)

@app.route('/wallet')
@login_required
def wallet():
    wallets = Wallet.query.filter_by(user_id=session['user_id']).all()
    return render_template('wallet.html', wallets=wallets)

@app.route('/add_wallet', methods=['GET', 'POST'])
@login_required
def add_wallet():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        protocol = request.form.get('protocol', '').strip()
        address = request.form.get('address', '').strip()

        if not all([name, protocol, address]):
            flash("Lütfen tüm alanları doldurun.", "error")
            return redirect(url_for('add_wallet'))

        new_wallet = Wallet(user_id=session['user_id'], name=name, protocol=protocol, address=address)
        db.session.add(new_wallet)
        db.session.commit()
        flash("Cüzdan başarıyla eklendi.", "success")
        return redirect(url_for('wallet'))

    return render_template('add_wallet.html')

@app.route('/invite')
@login_required
def invite():
    user = db.session.get(User, session['user_id'])
    return render_template('invite.html', user=user)

@app.route('/profile')
@login_required
def profile():
    user = db.session.get(User, session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/deposit_records')
@login_required
def deposit_records():
    records = TransactionLog.query.filter_by(user_id=session['user_id'], type='deposit').order_by(TransactionLog.timestamp.desc()).all()
    return render_template('deposit_records.html', records=records)

@app.route('/withdrawal')
@login_required
def withdrawal():
    user = db.session.get(User, session['user_id'])
    if not user.has_completed_any_vip:
        flash("Para çekebilmek için öncelikle en az bir VIP seviyesindeki tüm görevleri tamamlamanız gerekmektedir.", "error")
        return redirect(url_for('mine'))
    wallets = Wallet.query.filter_by(user_id=session['user_id']).all()
    return render_template('withdrawal.html', wallets=wallets, user=user)

@app.route('/request_withdrawal', methods=['POST'])
@login_required
def request_withdrawal():
    user = db.session.get(User, session['user_id'])
    if not user.has_completed_any_vip:
        flash("Para çekme yetkiniz yok.", "error")
        return redirect(url_for('mine'))
    
    wallet_id = request.form.get('wallet_id')
    try:
        amount = float(request.form.get('amount', 0))
    except (ValueError, TypeError):
        flash("Geçersiz miktar.", "error")
        return redirect(url_for('withdrawal'))
    
    if not wallet_id:
        flash("Lütfen bir cüzdan seçin.", "error")
    elif amount <= 0:
        flash("Çekim miktarı 0'dan büyük olmalı.", "error")
    elif user.balance < amount:
        flash("Yetersiz bakiye.", "error")
    else:
        user.balance -= amount
        new_log = TransactionLog(user_id=session['user_id'], type='withdrawal', amount=amount, status='pending')
        db.session.add(new_log)
        db.session.commit()
        flash("Para çekme talebiniz alındı ve inceleniyor.", "success")
        return redirect(url_for('mine'))
        
    return redirect(url_for('withdrawal'))

@app.route('/withdrawal_records')
@login_required
def withdrawal_records():
    records = TransactionLog.query.filter_by(user_id=session['user_id'], type='withdrawal').order_by(TransactionLog.timestamp.desc()).all()
    return render_template('withdrawal_records.html', records=records)

@app.route('/settings')
@login_required
def settings():
    user = db.session.get(User, session['user_id'])
    return render_template('settings.html', user=user)

@app.route('/task_detail/<int:level_id>')
@login_required
def task_detail(level_id):
    level = VipLevel.query.filter_by(level=level_id).first_or_404()
    user = db.session.get(User, session['user_id'])
    progress = UserTaskProgress.query.filter_by(user_id=user.id, vip_level=level_id).first()
    tasks_done = progress.tasks_completed if progress else 0

    # Bugünkü komisyonu hesapla
    today_commission = db.session.query(
        db.func.sum(TransactionLog.amount)
    ).filter(
        TransactionLog.user_id == user.id,
        TransactionLog.type == 'commission',
        db.func.date(TransactionLog.timestamp) == db.func.current_date()
    ).scalar() or 0.0

    return render_template(
        'task_detail.html',
        level=level,
        user=user,
        tasks_done=tasks_done,
        today_commission=round(today_commission, 2)
    )


# ----------------- VERİTABANI OLUŞTURMA KOMUTU -----------------
def populate_vip_levels():
    if VipLevel.query.first():
        print("VIP seviyeleri zaten mevcut.")
        return
    levels_data = [
        {'level': 1, 'name': 'Amazon', 'logo_url': '/static/images/amazon_logo.png', 'min_balance': 10, 'max_balance': 498, 'max_tasks': 25, 'commission_rate': 4},
        {'level': 2, 'name': 'Alibaba', 'logo_url': '/static/images/alibaba_logo.png', 'min_balance': 499, 'max_balance': 899, 'max_tasks': 25, 'commission_rate': 8},
        {'level': 3, 'name': 'Aliexpress', 'logo_url': '/static/images/aliexpress_logo.png', 'min_balance': 899, 'max_balance': 999999, 'max_tasks': 25, 'commission_rate': 12}
    ]
    for data in levels_data:
        db.session.add(VipLevel(**data))
    db.session.commit()
    print("VIP seviyeleri başarıyla eklendi.")

@app.cli.command("initdb")
def initdb_command():
    """Veritabanını temizler, yeniden oluşturur ve VIP seviyelerini ekler."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        populate_vip_levels()
        print('Veritabanı başarıyla sıfırlandı.')

@app.cli.command("create-admin")
def create_admin_command():
    """Yeni bir admin kullanıcısı oluşturur."""
    with app.app_context():
        username = input("Admin kullanıcı adı: ").strip()
        password = input("Admin şifresi: ").strip()
        if not username or not password:
            print("Kullanıcı adı ve şifre boş olamaz.")
            return
        if User.query.filter_by(username=username).first():
            print("Bu kullanıcı adı zaten mevcut.")
            return
        while True:
            code = ''.join(random.choices(string.digits, k=6))
            if not User.query.filter_by(invitation_code=code).first():
                break
        admin_user = User(username=username, password=generate_password_hash(password), invitation_code=code, is_admin=True)
        db.session.add(admin_user)
        db.session.commit()
        print(f"Admin '{username}' oluşturuldu.")




with app.app_context():
    db.create_all()
    print("✅ PostgreSQL tabloları oluşturuldu.")

@app.before_request
def ensure_admins():
    admin_usernames = ["enesbozkurt", "cgrunl"]

    for username in admin_usernames:
        user = User.query.filter_by(username=username).first()
        if user:
            if not user.is_admin:
                user.is_admin = True
                db.session.commit()
        else:
            # Eğer kullanıcı yoksa otomatik oluştur
            new_user = User(
                username=username,
                password=generate_password_hash("123456"),   # Şifreyi hash'leyelim
                invitation_code=''.join(random.choices(string.digits, k=6)),  # Zorunlu alan
                is_admin=True
            )
            db.session.add(new_user)
            db.session.commit()


# ----------------- UYGULAMA ÇALIŞTIR -----------------



if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)


