1. Senaryo Adı ve Kullanım Hikayesi
Senaryo Adı: S59 — Bitki Bakımı Asistanı
Kullanım Hikayesi: Bitki Bakımı Asistanı, evinde bitki yetiştiren kişilerin bitkilerinin sağlığıyla ilgili karşılaştıkları temel sorunlarda (sararma, solma, fazla sulama vb.) ilk yardım niteliğinde tavsiyeler verir. Kullanıcı "Bitkimin yaprakları sarardı, ne yapmalıyım?" diye sorar; bot temel bakım adımlarını söyler veya durumun ciddiyetine göre konuyu bir botanik uzmanına aktarır.

2. Hedef Kullanıcı
Hedef kullanıcı, evinde, ofisinde veya balkonunda hobi amaçlı süs bitkisi, çiçek veya sebze yetiştiren ancak bitki hastalıkları konusunda detaylı bilgisi olmayan amatör bitki severlerdir. Kullanıcılar bu botu, bitkilerinde beklenmedik bir renk değişimi, kuruma veya yaprak dökülmesi gördüklerinde panik anında anında tavsiye almak için kullanırlar.

3. HOOTL Modu Davranışı
HOOTL (Human-Out-Of-The-Loop) modunda bot, sisteminde (bilgi.txt) tanımlı olan genel ve sık karşılaşılan bakım sorunlarına doğru cevap verir (örneğin; fazla sulama belirtileri, güneş ihtiyacı, toprak değişimi sıklığı gibi basit konularda). Ancak bitki türüne özgü özel kompleks durumlar veya sistemine tanımlanmamış sorular sorulduğunda yanlış, eksik cevap verebilir veya "Bu sorunun cevabını bilmiyorum" yanıtını döndürür. Bot bu modda tamamen otonomdur.

4. HITL Modu Operatörü
HITL (Human-In-The-Loop) modunda çalışan operatör, bitki patolojisi ve genel bitki bakımı konularında uzman olan bir "Ziraat Mühendisi" veya deneyimli bir "Botanik Uzmanı"dır.

5. HOTL Modu İnsana Havale Kuralı ve Nedeni
HOTL (Human-On-The-Loop) modunda bot, kullanıcının mesajında "böcek", "çürüme", "mantar", "hastalık", "kurt" veya "ölüyor" gibi riski yüksek kelimeler (Risk Kelimesi stratejisi) yakaladığında VEYA kullanıcının sorduğu sorunun cevabı sistemde bulunamadığında (Belirsizlik stratejisi) durumu doğrudan insana (Botanik Uzmanına) havale eder. 
NİYE? Çünkü basit sulama veya ışık hataları botun yönlendirmesiyle kolayca çözülebilir ve zaman kritik değildir. Ancak mantar hastalıkları veya zararlı böcek istilası, bitkinin saatler veya günler içinde ölmesine, hatta diğer bitkilere sıçramasına yol açabilir. Botun bu tür hayati durumlarda yanlış bir öneride bulunması bitkinin tamamen kaybedilmesine sebep olacağından, bu tür riskli kelimelerde empati kurabilen ve daha detaylı analiz yapabilen bir insanın devreye girmesi hayati önem taşır.

6. bilgi.txt Taslağı
sarı|Bitkinizi fazla sulamış olabilirsiniz. Toprağın kurumasını bekleyin ve sulama sıklığını azaltın.
sarar|Bitkinizi fazla sulamış olabilirsiniz. Toprağın kurumasını bekleyin ve sulama sıklığını azaltın.
kuru|Bitkiniz susuz kalmış veya çok fazla doğrudan güneş ışığına maruz kalmış olabilir.
kahverengi|Ortamdaki nem oranı düşük olabilir. Yapraklara su püskürterek nemi artırmayı deneyin.
soldu|Köklerde havasızlık veya ani sıcaklık değişimi olmuş olabilir. Ortamı havalandırın.
dökül|Bitki strese girmiş olabilir. Yerini veya toprağını yakın zamanda değiştirdiyseniz bir süre adapte olmasını bekleyin.
döktü|Bitki strese girmiş olabilir. Yerini veya toprağını yakın zamanda değiştirdiyseniz bir süre adapte olmasını bekleyin.
güneş|Çoğu salon bitkisi doğrudan güneş ışığı yerine filtrelenmiş aydınlık ortamları sever.
su|Genel kural olarak toprağın üst kısmı (2-3 cm) tamamen kurudukça sulama yapmalısınız.
gübre|Bitkinize sadece ilkbahar ve yaz aylarında, büyüme döneminde gübre vermelisiniz.
saksı|Saksı değişimi genellikle ilkbahar aylarında, mevcut saksı köklerle dolduğunda yapılmalıdır.
karanlık|Işık yetersizliği bitkinizin boyunun uzamasına ama cılız kalmasına neden olur. Daha aydınlık bir yere alın.
toz|Yaprakların tozlanması bitkinin fotosentez yapmasını zorlaştırır. Nemli bir bezle nazikçe silin.
kök|Bitkinizin kökleri saksı altındaki deliklerden çıkıyorsa, bir boy büyük saksıya geçme vakti gelmiştir.