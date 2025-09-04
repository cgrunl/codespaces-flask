-- Eskiden var olan tabloları temizleyerek çakışmaları önler.
DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS vip_level;
DROP TABLE IF EXISTS transaction_log;


-- Kullanıcı bilgilerini, bakiyeyi ve davet kodlarını saklayan ana tablo.
CREATE TABLE user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  invitation_code TEXT UNIQUE NOT NULL, -- Her kullanıcının kendine özel, başkalarını davet edeceği kod.
  invited_by INTEGER,                   -- Kullanıcıyı davet edenin ID'si. Boş olabilir (NULL).
  balance REAL NOT NULL DEFAULT 0,
  vip_level INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- Görev/Menü sayfasındaki VIP seviyelerinin kurallarını tanımlayan tablo.
CREATE TABLE vip_level (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level INTEGER UNIQUE NOT NULL,
    name TEXT NOT NULL,
    logo_url TEXT,
    min_balance REAL NOT NULL,
    max_balance REAL,
    commission_rate REAL NOT NULL
);


-- Tüm para yatırma, çekme ve kazanç geçmişini kaydeden işlem tablosu.
CREATE TABLE transaction_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    type TEXT NOT NULL, -- 'deposit', 'withdrawal', 'commission' vb.
    amount REAL NOT NULL,
    status TEXT NOT NULL, -- 'completed', 'pending', 'failed'
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user (id)
);