import sys
import time
import socket
import difflib

def bilgi_yukle():
    # Bilgileri txt dosyasından okuyup sözlüğe atıyoruz
    bilgi_tabani = {}
    try:
        with open('bilgi.txt', 'r', encoding='utf-8') as f:
            for satir in f:
                if '|' in satir:
                    anahtar, deger = satir.strip().split('|', 1)
                    bilgi_tabani[anahtar] = deger
    except FileNotFoundError:
        print("Hata: bilgi.txt dosyası bulunamadı.")
    return bilgi_tabani

def uzmana_sor(soru):
    # Botun tıkandığı yerde soruyu soket üzerinden uzmana (expert.py) yolluyoruz
    print("\n[Sistem] İMDAT! Uzmana bağlanılıyor. Lütfen bekleyin...")
    try:
        istemci_soketi = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Uzmanımız localhost'ta 5000 portunu dinliyor
        istemci_soketi.connect(('localhost', 5000))
        istemci_soketi.sendall(soru.encode('utf-8'))
        
        # Uzman cevap yazana kadar bekle
        cevap = istemci_soketi.recv(4096).decode('utf-8')
        istemci_soketi.close()
        return cevap
    except ConnectionRefusedError:
        return "[Sistem Hatası] Uzmana ulaşılamıyor. Lütfen expert.py'nin çalıştığından emin olun."
    except Exception as hata:
        return f"[Sistem Hatası] Beklenmeyen bir hata oluştu: {hata}"

def yaklasik_esitlik(kullanici_girdisi, bilgi_sozlugu):
    kullanici_girdisi_kucuk = kullanici_girdisi.lower()
    kelimeler = kullanici_girdisi_kucuk.split()

    en_iyi_anahtar = None
    en_iyi_skor = 0
    
    for anahtar in bilgi_sozlugu.keys():
        anahtar_kucuk = anahtar.lower()
        
        # Eğer anahtar tam olarak kelimelerin içinde veya cümlenin içinde geçiyorsa
        if anahtar_kucuk in kullanici_girdisi_kucuk:
            return anahtar, 100.0
            
        # Girdi kelimeleri ile anahtar arasında benzerlik kontrolü (difflib)
        for kelime in kelimeler:
            benzerlik = difflib.SequenceMatcher(None, anahtar_kucuk, kelime).ratio() * 100
            
            # Eğer skor mevcut en iyi skordan fazlaysa güncelle
            if benzerlik > en_iyi_skor:
                en_iyi_skor = benzerlik
                en_iyi_anahtar = anahtar

    return en_iyi_anahtar, en_iyi_skor

def cevap_bul(soru, bilgi_tabani):
    # Kendi yazdığımız eşleştirme fonksiyonuyla soruyu değerlendiriyoruz
    en_iyi_anahtar, skor = yaklasik_esitlik(soru, bilgi_tabani)
    return en_iyi_anahtar, skor

def main():
    # Programı terminalden çalıştırırken hangi modda açacağımızı kontrol ediyoruz
    if len(sys.argv) < 2 or sys.argv[1] not in ['hootl', 'hitl', 'hotl']:
        print("Kullanım: python bot.py [hootl|hitl|hotl]")
        sys.exit(1)
        
    mod = sys.argv[1]
    bilgi_tabani = bilgi_yukle()
    
    print("==================================================")
    print("🌿 Bitki Bakımı Asistanına Hoş Geldiniz! 🌿") 
    print("UYARI: Bu bot kesin ziraat veya tıbbi tavsiye vermez.")
    print("Ciddi durumlarda mutlaka bir uzmana başvurun.")
    print(f"Aktif Mod: {mod.upper()}")
    print("Çıkmak için 'çıkış' yazabilirsiniz.")
    print("==================================================")
    
    # Sürekli dönen mesajlaşma döngümüz
    while True:
        kullanici_girdisi = input("\nSen: ")
        if kullanici_girdisi.lower() in ['çıkış', 'kapat', 'exit', 'quit']:
            print("Bot: Görüşmek üzere! Bitkilerinize iyi bakın.")
            break
            
        if mod == 'hootl':
            # HOOTL Modu: Bot her şeyi kendi bilir, uzmandan hiç yardım almaz
            en_iyi_anahtar, skor = cevap_bul(kullanici_girdisi, bilgi_tabani)
            if skor >= 70:
                print(f"Bot: Bunu mu demek istediniz: '{en_iyi_anahtar}'? (Benzerlik Skoru: %{skor:.2f})")
                print("Bot:", bilgi_tabani[en_iyi_anahtar])
            else:
                print(f"Bot: Üzgünüm, sorunuzu tam anlayamadım (Skor: %{skor:.2f}). HOOTL modunda uzmana bağlanılamaz.")
                
        elif mod == 'hitl':
            # HITL Modu: Bot aradan çekilir, gelen her soruyu direkt uzmana havale eder
            cevap = uzmana_sor(kullanici_girdisi)
            print("Botanik Uzmanı:", cevap)
            
        elif mod == 'hotl':
            # HOTL Modu: Bot hem kendi cevap vermeye çalışır, hem de şüpheli durumlarda uzmana paslar
            riskli_kelimeler = ["böcek", "çürüme", "mantar", "hastalık", "kurt", "ölüyor"]
            risk_var_mi = False
            
            # Acil ve riskli kelime kontrolü
            for kelime in riskli_kelimeler:
                if kelime in kullanici_girdisi.lower():
                    risk_var_mi = True
                    break
            
            en_iyi_anahtar, skor = cevap_bul(kullanici_girdisi, bilgi_tabani)
            
            # Eğer riskli kelime varsa skora bakmadan direkt uzmana yönlendiriyoruz
            if risk_var_mi:
                print("Bot: Mesajınızda bitkiniz için riskli olabilecek bir durum tespit ettim.")
                uzman_cevabi = uzmana_sor(kullanici_girdisi)
                print("Botanik Uzmanı:", uzman_cevabi)
            
            # Eğer risk yoksa ve bot %70'ten fazla eminse kendisi cevaplıyor
            elif skor >= 70:
                print(f"Bot: Bunu mu demek istediniz: '{en_iyi_anahtar}'? (Benzerlik Skoru: %{skor:.2f})")
                print("Bot:", bilgi_tabani[en_iyi_anahtar])
                
            # Eğer bot anlayamadıysa İMDAT diyip uzmana yolluyor
            else:
                print(f"Bot: Bu sorunun cevabını tam çıkaramadım (Skor: %{skor:.2f}).")
                uzman_cevabi = uzmana_sor(kullanici_girdisi)
                print("Botanik Uzmanı:", uzman_cevabi)

if __name__ == "__main__":
    main()