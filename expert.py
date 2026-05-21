import socket
import sys

def main():
    # Programı çalıştırınca bizi karşılayacak olan uzman (operatör) ekranı
    print("==================================================")
    print("👨‍🌾 Botanik Uzmanı (Operatör) Paneline Hoş Geldiniz")
    print("Sistemden gelecek olan vakalar bekleniyor... (SOCKET İLE)")
    print("Çıkmak için CTRL+C yapabilirsiniz.")
    print("==================================================")
    
    # Soket bağlantısı için yerel ağ adresimizi ve portumuzu ayarlıyoruz
    AG_ADRESI = 'localhost'
    PORT = 5000
    
    sunucu_soketi = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Kodu arka arkaya çalıştırınca "Address already in use" hatası almamak için bu ayarı ekliyoruz
    sunucu_soketi.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        sunucu_soketi.bind((AG_ADRESI, PORT))
        # Bot sadece 1 kişiyle konuşacağı için aynı anda 1 bağlantı dinlememiz yeterli
        sunucu_soketi.listen(1) 
    except Exception as hata:
        print(f"Socket başlatılamadı: {hata}")
        sys.exit(1)
        
    try:
        # Sonsuz döngü: Bütün gün bot'tan gelecek imdat çağrılarını bekliyoruz
        while True:
            # Biri bize bağlanana kadar kod burada bekliyor
            istemci_soketi, adres = sunucu_soketi.accept()
            
            # Bağlantı gelince botun yolladığı soruyu alıyoruz
            soru_verisi = istemci_soketi.recv(1024)
            if not soru_verisi:
                istemci_soketi.close()
                continue
                
            soru = soru_verisi.decode('utf-8')
            
            # Soruyu ekrana basıp operatörden (bizden) klavyeyle cevap yazmasını istiyoruz
            print(f"\n[YENİ VAKA GELDİ]: Bota bir soru geldi, ne cevap verelim?")
            print(f"Kullanıcının sorusu: {soru}")
            
            cevap = input("Cevabınız: ")
            
            # Yazdığımız cevabı tekrar bota (bot.py'ye) yolluyoruz
            istemci_soketi.sendall(cevap.encode('utf-8'))
            print("Cevap sisteme iletildi. Yeni sorular bekleniyor...")
            
            # İşimiz bittiği için o soruluk bağlantıyı kapatıyoruz
            istemci_soketi.close()
            
    except KeyboardInterrupt:
        # CTRL+C yapınca program çökmesin, düzgünce kapansın diye bunu koyduk
        print("\nÇıkış yapılıyor...")
    finally:
        sunucu_soketi.close()

if __name__ == "__main__":
    main()
