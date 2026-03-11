import subprocess
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule
import time
import os
from datetime import datetime

# ==========================================
# 1. AYARLAR 
# ==========================================

# Veritabanı Ayarları
DB_SERVER = '94.73.151.2'
DB_NAME = 'Yeni_Mekmar_DB'
DB_USER = 'userEC52E044DE'
DB_PASS = 'POlb33D8PQlo68S' # <-- SQL Şifreni Yaz

# E-Posta Ayarları
SMTP_HOST = 'mail.mekmar.com'
SMTP_PORT = 587
SMTP_USER = 'goz@mekmar.com'
SMTP_PASS = '_bwt64h-3SR_-G2O' # <-- Mail Şifreni Yaz
TARGET_EMAIL = 'bilgiislem@mekmar.com'  

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

# ==========================================
# 2. YARDIMCI FONKSİYONLAR
# ==========================================

def send_email(subject, html_content):
    """E-posta gönderimini sağlar"""
    msg = MIMEMultipart("alternative")
    msg['Subject'] = subject
    msg['From'] = f"Mekmar Yedekleme <{SMTP_USER}>"
    msg['To'] = TARGET_EMAIL

    part = MIMEText(html_content, 'html')
    msg.attach(part)

    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.ehlo()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, TARGET_EMAIL, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"❌ E-posta gönderim hatası: {e}")

def perform_remote_backup():
    """Uzak veritabanından Schema + Data çekip yerel sunucuya kaydeder"""
    now = datetime.now()
    date_string = now.strftime("%Y_%m_%d_%H%M")
    
    # Kaydedilecek dosyanın tam yolu
    backup_file_name = f"{DB_NAME}_{date_string}.sql"
    local_backup_path = os.path.join(BACKUP_DIR, backup_file_name)
    
    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] ⏳ Uzak sunucudan yedek çekiliyor... Lütfen bekleyin.")

    # ÇÖZÜM: Komutun sonuna -f parametresi ekleyerek dosyayı doğrudan scripter'ın oluşturmasını sağlıyoruz.
    command = f"python -m mssqlscripter -S {DB_SERVER} -d {DB_NAME} -U {DB_USER} -P \"{DB_PASS}\" --schema-and-data -f \"{local_backup_path}\""

    try:
        # Python artık dosyayı kendi yazmaya çalışmıyor, sadece komutu tetikliyor
        process = subprocess.run(command, shell=True, stderr=subprocess.PIPE, universal_newlines=True, encoding="utf-8")
        # Eğer işlem başarıyla bittiyse (Return code 0 ise)
        if process.returncode == 0:
            file_size_mb = os.path.getsize(local_backup_path) / (1024 * 1024)
            print(f"✅ Yedekleme başarılı! Dosya Boyutu: {file_size_mb:.2f} MB")

            success_html = f"""
            <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #4fab9f; border-radius: 8px;">
                <h2 style="color: #4fab9f;">Yedekleme İşlemi Başarılı</h2>
                <p>Uzak veritabanının yapısı ve verileri (Schema + Data) başarıyla çekildi.</p>
                <hr style="border:0; border-top: 1px solid #eee;" />
                <p><b>Veritabanı:</b> {DB_NAME}</p>
                <p><b>Kaydedilen Yer:</b> {local_backup_path}</p>
                <p><b>Dosya Boyutu:</b> {file_size_mb:.2f} MB</p>
                <p><b>Tarih/Saat:</b> {now.strftime('%d.%m.%Y %H:%M:%S')}</p>
            </div>
            """
            send_email(f"✅ BAŞARILI: Veritabanı Yedeği Alındı ({date_string})", success_html)

        else:
            # Komut başarısız olduysa hatayı yakala
            error_msg = process.stderr
            raise Exception(error_msg)

    except Exception as e:
        print(f"❌ Yedekleme Hatası: {e}")
        
        # Boş oluşan bozuk dosyayı sil
        if os.path.exists(local_backup_path) and os.path.getsize(local_backup_path) == 0:
            os.remove(local_backup_path)

        error_html = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #ef4444; border-radius: 8px;">
            <h2 style="color: #ef4444;">Yedekleme İşlemi BAŞARISIZ!</h2>
            <p>Uzak veritabanından veri çekilirken bir hata oluştu.</p>
            <hr style="border:0; border-top: 1px solid #eee;" />
            <p><b>Hata Detayı:</b><br/> {str(e)}</p>
        </div>
        """
        send_email(f"❌ HATA: Veritabanı Yedeği ALINAMADI!", error_html)
# ==========================================
# 3. ZAMANLAYICIYI BAŞLAT 
# ==========================================

print("🚀 Uzak Yedekleme (Scripter) Servisi Başlatıldı...")

# Her gece 03:00'da çalışır
schedule.every().day.at("03:00").do(perform_remote_backup)

# Sonsuz döngüde bekle
while True:
    schedule.run_pending()
    time.sleep(60)