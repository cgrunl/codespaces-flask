-- Önceki tabloları temizleyerek çakışmaları önler.
DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS vip_level;
DROP TABLE IF EXISTS transaction_log;
DROP TABLE IF EXISTS wallet;
DROP TABLE IF EXISTS user_task_progress;

-- Kullanıcı bilgilerini, bakiyeyi ve yeni kuralları saklayan ana tablo.
CREATE TABLE user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  invitation_code TEXT UNIQUE NOT NULL,
  invited_by INTEGER,
  balance REAL NOT NULL DEFAULT 0,
  vip_level INTEGER NOT NULL DEFAULT 1,
  is_admin BOOLEAN NOT NULL DEFAULT 0,
  has_completed_any_vip BOOLEAN NOT NULL DEFAULT 0, -- Para çekme kilidi için eklendi
  checkpoint_target REAL NOT NULL DEFAULT 0, -- Görev kontrol noktası için eklendi
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- VIP seviyelerinin kurallarını tanımlayan tablo.
CREATE TABLE vip_level (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level INTEGER UNIQUE NOT NULL,
    name TEXT NOT NULL,
    logo_url TEXT,
    min_balance REAL NOT NULL,
    max_tasks INTEGER NOT NULL DEFAULT 25, -- Görev limiti için eklendi
    commission_rate REAL NOT NULL
);

-- Kullanıcının her VIP seviyesindeki görev ilerlemesini saklayan YENİ tablo.
CREATE TABLE user_task_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    vip_level INTEGER NOT NULL,
    tasks_completed INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES user (id)
);

-- Tüm finansal işlemleri kaydeden işlem tablosu.
CREATE TABLE transaction_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    amount REAL NOT NULL,
    status TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user (id)
);

-- Kullanıcıların para çekme cüzdanlarını saklayan tablo.
CREATE TABLE wallet (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    protocol TEXT NOT NULL,
    address TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user (id)
);

