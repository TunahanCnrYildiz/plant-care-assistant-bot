import sys
import time
import socket
import os
import joblib
import json
import urllib.request
import builtins
import locale

# Safe print wrapper to prevent UnicodeEncodeError on Windows terminals
def safe_print(*args, **kwargs):
    encoding = sys.stdout.encoding or 'utf-8'
    new_args = []
    for arg in args:
        if isinstance(arg, str):
            new_args.append(arg.encode(encoding, errors='replace').decode(encoding))
        else:
            new_args.append(arg)
    builtins.print(*new_args, **kwargs)

# Override the default print function globally
print = safe_print

# Translation dictionary for internationalization (i18n)
LANG_STRINGS = {
    'tr': {
        'system_prefix': '[Sistem]',
        'ai_generating': 'Yerel yapay zeka (Ollama) yanıt üretiyor. Lütfen bekleyin...',
        'ai_offline': '[Sistem Hatası] Ollama sunucusuna ulaşılamadı. Lütfen Ollama uygulamasının açık olduğundan emin olun.',
        'ai_error': '[Sistem Hatası] Yapay zeka ile haberleşirken hata oluştu: {error}',
        'model_not_found': '[Hata] Eğitilmiş model dosyaları (model.joblib veya vectorizer.joblib) bulunamadı.\nLütfen önce modelinizi eğitin: python train.py',
        'knowledge_base_not_found': 'Hata: knowledge.txt dosyası bulunamadı.',
        'welcome_border': '==================================================',
        'welcome_title': 'Bitki Bakimi Asistanina Hos Geldiniz!',
        'welcome_warning': 'UYARI: Bu bot kesin ziraat veya tibbi tavsiye vermez.',
        'welcome_consult': 'Ciddi durumlarda mutlaka bir uzmana basvurun.',
        'active_mode': 'Aktif Mod: {mode}',
        'exit_instruction': "Cikmak icin 'cikis' yazabilirsiniz.",
        'exit_message': 'Bot: Görüşmek üzere! Bitkilerinize iyi bakın.',
        'user_prompt': 'Sen: ',
        'bot_did_you_mean': "Bot: Bunu mu demek istediniz: '{key}'? (Güven Skoru: %{score:.2f})",
        'risk_detected': 'Mesajınızda bitkiniz için riskli olabilecek bir durum tespit ettim.',
        'ai_offline_fallback': 'Yerel yapay zeka sunucusuna bağlanılamadı. Uzmana aktarılıyorsunuz...',
        'ask_expert_msg': 'İMDAT! Uzmana bağlanılıyor. Lütfen bekleyin...',
        'expert_offline': '[Sistem Hatası] Uzmana ulaşılamıyor. Lütfen expert.py\'nin çalıştığından emin olun.',
        'expert_error': '[Sistem Hatası] Beklenmeyen bir hata oluştu: {error}',
        'bot_prefix': 'Bot: ',
        'expert_prefix': 'Botanik Uzmanı: ',
        'ai_prefix': 'Yapay Zeka Asistanı: ',
        'usage_error': "Kullanım: python bot.py [hootl|hitl|hotl] [--lang tr|en]",
        'unrelated_response': "Ben sadece bitki bakımı, toprak, sulama, gübreleme ve zirai konularla ilgili sorulara cevap verebilirim. Lütfen bitkilerinizle ilgili bir soru sorunuz.",
        'expert_ended': 'Sohbet oturumu uzman tarafından sonlandırılmıştır.'
    },
    'en': {
        'system_prefix': '[System]',
        'ai_generating': 'Local AI (Ollama) is generating response. Please wait...',
        'ai_offline': '[System Error] Ollama server could not be reached. Please ensure the Ollama application is running.',
        'ai_error': '[System Error] An error occurred while communicating with AI: {error}',
        'model_not_found': '[Error] Trained model files (model.joblib or vectorizer.joblib) not found.\nPlease train your model first: python train.py',
        'knowledge_base_not_found': 'Error: knowledge.txt file not found.',
        'welcome_border': '==================================================',
        'welcome_title': 'Welcome to the Plant Care Assistant!',
        'welcome_warning': 'WARNING: This bot does not provide definitive agricultural or medical advice.',
        'welcome_consult': 'For serious cases, always consult an expert.',
        'active_mode': 'Active Mode: {mode}',
        'exit_instruction': "You can type 'exit' to quit.",
        'exit_message': 'Bot: Goodbye! Take good care of your plants.',
        'user_prompt': 'You: ',
        'bot_did_you_mean': "Bot: Did you mean: '{key}'? (Confidence Score: %{score:.2f})",
        'risk_detected': 'I detected a potentially risky condition for your plant in your message.',
        'ai_offline_fallback': 'Local AI server could not be reached. Transferring you to the expert...',
        'ask_expert_msg': 'SOS! Connecting to expert. Please wait...',
        'expert_offline': '[System Error] Expert cannot be reached. Please ensure expert.py is running.',
        'expert_error': '[System Error] An unexpected error occurred: {error}',
        'bot_prefix': 'Bot: ',
        'expert_prefix': 'Botanist Expert: ',
        'ai_prefix': 'AI Assistant: ',
        'usage_error': "Usage: python bot.py [hootl|hitl|hotl] [--lang tr|en]",
        'unrelated_response': "I can only answer questions related to plant care, soil, watering, fertilizing, and agricultural topics. Please ask a question about your plants.",
        'expert_ended': 'The chat session has been terminated by the expert.'
    }
}

# Auto-detect OS default language
def get_default_language():
    try:
        sys_lang = locale.getlocale()[0]
        if sys_lang:
            sys_lang_lower = sys_lang.lower()
            if sys_lang_lower.startswith('tr') or 'turkish' in sys_lang_lower:
                return 'tr'
    except:
        pass
    return 'en'

# Parse arguments for mode and optional language
def parse_arguments():
    lang = get_default_language()
    if '--lang' in sys.argv:
        try:
            lang_idx = sys.argv.index('--lang')
            if lang_idx + 1 < len(sys.argv):
                provided_lang = sys.argv[lang_idx + 1].lower()
                if provided_lang in ['tr', 'en']:
                    lang = provided_lang
                sys.argv.pop(lang_idx + 1)
                sys.argv.pop(lang_idx)
        except ValueError:
            pass
            
    if len(sys.argv) < 2 or sys.argv[1] not in ['hootl', 'hitl', 'hotl']:
        print(LANG_STRINGS[lang]['usage_error'])
        sys.exit(1)
        
    mode = sys.argv[1]
    return mode, lang

def load_knowledge_base(lang):
    # Load knowledge base from the txt file and parse it into a dictionary
    knowledge_base = {}
    try:
        with open('knowledge.txt', 'r', encoding='utf-8') as f:
            for line in f:
                if '|' in line:
                    key, value = line.strip().split('|', 1)
                    knowledge_base[key] = value
    except FileNotFoundError:
        print(LANG_STRINGS[lang]['knowledge_base_not_found'])
    return knowledge_base

def detect_language(text):
    text_lower = text.lower()
    
    # 1. Turkish specific characters (most reliable indicator if present)
    tr_chars = set("ışğçöüı")
    if any(char in text_lower for char in tr_chars):
        return 'tr'
        
    # 2. Common words list comparison
    tr_words = {
        "ve", "bir", "bu", "icin", "için", "mi", "mı", "mu", "mü", "de", "da", "ama", "çünkü", "cunku", 
        "nedir", "nasıl", "nasil", "bakimi", "bakımı", "bitki", "yaprak", "solma", "sararma", "sulama", 
        "toprak", "gubre", "gübre", "cicek", "çiçek", "su", "vermeliyim", "ediyor",
        "merhaba", "selam", "nasılsın", "nasilsin", "ne", "nelerdir", "kim", "kimdir", "nerede", "nereye", 
        "ne zaman", "niye", "neden", "bilgi", "ver", "yaz", "kod", "hava", "durumu", "bugün", "bugun", 
        "fıkra", "fikra", "anlat", "yemek", "tarifi", "lütfen", "lutfen", "teşekkürler", "tesekkurler", 
        "iyi", "kötü", "kotu", "evet", "hayır", "hayir", "tamam", "bana", "sana", "ben", "sen", "o", 
        "biz", "siz", "onlar", "yardım", "yardim", "et", "yap", "anlatır", "anlatir", "mısın", "misin"
    }
    en_words = {
        "the", "be", "to", "of", "and", "a", "in", "that", "have", "it", "for", "not", "on", "with", 
        "as", "you", "do", "at", "this", "but", "by", "from", "they", "we", "or", "an", "will", "my", 
        "would", "there", "their", "what", "grow", "plant", "flower", "leaf", "care", "water", "soil", 
        "fertilizer", "how", "why", "is", "are", "can", "about", "your", "my",
        "hello", "hi", "where", "who", "which", "when", "computer", "tell", "show", "give", "write", 
        "code", "run", "help", "could", "should", "please", "thank", "thanks", "good", "bad", "yes", 
        "no", "ok", "okay", "today", "weather", "recipe", "joke", "me", "him", "her", "us", "them", 
        "i", "about", "recommend", "movie", "history", "fastest", "car", "temperature"
    }
                
    import re
    words = re.findall(r'\b\w+\b', text_lower)
    
    tr_count = sum(1 for w in words if w in tr_words)
    en_count = sum(1 for w in words if w in en_words)
    
    if tr_count > en_count:
        return 'tr'
    elif en_count > tr_count:
        return 'en'
        
    return None

def is_plant_related(text):
    text_lower = text.lower()
    
    # Split into words using regex
    import re
    words = set(re.findall(r'\b\w+\b', text_lower))
    
    # Whole word matches (words that must match exactly)
    exact_terms = {
        "bitki", "bitkim", "bitkinin", "bitkiler", "bitkisi", "bitkilerim",
        "çiçek", "çiçeğim", "çiçeğin", "çiçekler", "çiçeği", "cicek", "cicegim",
        "yaprak", "yaprağım", "yaprağın", "yapraklar", "yaprağı", "yaprakları", "yapragı",
        "kök", "kökler", "kökü", "kökleri", "kok", "kokler",
        "toprak", "toprağı", "toprağın", "topraklar", "toprakları",
        "saksı", "saksım", "saksının", "saksısı", "saksıyı", "saksi",
        "su", "suyu", "suyun", "sulama", "sulamak", "sulayalım", "sulanmalı",
        "gübre", "gübresi", "gübreleme", "gubre",
        "vitamin", "vitamini", "besin", "besini",
        "güneş", "güneşi", "gunes",
        "ışık", "ışığı", "isik",
        "karanlık", "karanlik",
        "gölge", "golge",
        "toz", "tozu", "tozlanma",
        "böcek", "böcekler", "bocek",
        "mantar", "mantarı",
        "hastalık", "hastalığı", "hastaliği", "hastalik",
        "kurt", "kurtlar",
        "çürüme", "çürümüş", "curume",
        "nem", "nemi", "nemli",
        "ilaç", "ilacı", "ilaçlama", "ilac",
        "haşere", "hasere",
        "fide", "fidan",
        "ağaç", "agac",
        "lavanta", "lavantam",
        "gül", "gülü", "gul",
        "papatya", "orkide", "kaktüs", "kaktus", "sukulent",
        "nane", "fesleğen", "feslegen", "biber", "domates",
        "botanik", "tarım", "tarim", "ziraat", "drenaj", "budama",
        # English terms
        "plant", "plants", "flower", "flowers", "leaf", "leaves", "stem", "stems", "root", "roots",
        "soil", "soils", "pot", "pots", "repotting", "water", "watering", "fertilizer", "fertilizers",
        "nutrient", "nutrients", "sun", "sunlight", "light", "lights", "dark", "darkness", "shade",
        "dust", "dusty", "wipe", "wiping", "clean", "cleaning", "bug", "bugs", "fungus", "fungi",
        "pest", "pests", "disease", "diseases", "rot", "rotting", "wilt", "wilting", "dry", "drying",
        "yellow", "yellowing", "brown", "browning", "spot", "spots", "drop", "dropping", "care",
        "grow", "growing", "seed", "seeds", "agriculture", "pesticide", "pesticides", "lavender",
        "rose", "roses", "orchid", "orchids", "cactus", "cacti", "succulent", "succulents", "mint",
        "basil", "pepper", "peppers", "tomato", "tomatoes", "tree", "trees", "drainage", "humidity",
        "botany", "botanist"
    }
    
    # Check if there is any intersection
    if words.intersection(exact_terms):
        return True
        
    # Substring matches for longer stems (where exact match is too restrictive, but safe from false matches)
    stems = [
        "sarar", "sararm", "sarari", 
        "kuruyor", "kurum", "kurudu", "kurus", 
        "soldu", "soluyor", "solma", 
        "dökül", "dokul", 
        "çürü", "curu", 
        "yetiş", "yetis"
    ]
    for stem in stems:
        for word in words:
            if word.startswith(stem):
                return True
                
    return False

def ask_local_ai(question, lang, chat_history=None):
    if chat_history is None:
        chat_history = []

    # Programmatically detect prompt language to enforce correct system prompt
    detected_lang = detect_language(question)
    active_lang = detected_lang if detected_lang else lang

    # Sleek in-place thinking status indicator (without line break)
    thinking_msg = f"{LANG_STRINGS[active_lang]['system_prefix']} {LANG_STRINGS[active_lang]['ai_prefix'].strip()} is thinking..." if active_lang == 'en' else f"{LANG_STRINGS[active_lang]['system_prefix']} {LANG_STRINGS[active_lang]['ai_prefix'].strip()} düşünüyor..."
    sys.stdout.write(f"\r{thinking_msg}")
    sys.stdout.flush()

    # Format the sliding window conversation history to pass to prompt
    history_str = ""
    if chat_history:
        if active_lang == 'tr':
            history_str = "KONUŞMA GEÇMİŞİ (BAĞLAM):\n"
            for user_msg, assistant_msg in chat_history:
                history_str += f"Soru: {user_msg}\nCevap: {assistant_msg}\n"
            history_str += "\n"
        else:
            history_str = "CONVERSATION HISTORY (CONTEXT):\n"
            for user_msg, assistant_msg in chat_history:
                history_str += f"Question: {user_msg}\nAnswer: {assistant_msg}\n"
            history_str += "\n"

    url = "http://localhost:11434/api/generate"
    
    # Store links and recommendation rules (configurable template)
    SHOP_ADDRESS = "[SITENIZ.COM]"  # Modify this with your actual domain name later
    FERTILIZER_LINK = f"www.{SHOP_ADDRESS}/gubreler"
    POT_LINK = f"www.{SHOP_ADDRESS}/saksilar"
    SOIL_LINK = f"www.{SHOP_ADDRESS}/topraklar"
    
    # Instruct the model using a system prompt corresponding to the active language
    if active_lang == 'tr':
        prompt_with_system = (
            "Sen ev bitkileri konusunda uzmanlaşmış yardımcı bir botanik asistanısın. "
            "Yalnızca ev bitkileri, bitki bakımı, sulama, toprak, gübreleme ve zirai konularla ilgili sorulara cevap ver. "
            "Bunlar dışındaki alakasız sorulara cevap vermeyi kesinlikle reddet ve kibarca sadece bitkiler konusunda yardımcı olabileceğini belirt.\n\n"
            "Sorulan soruyu kısa, anlaşılır ve pratik bir şekilde Türkçe olarak yanıtla.\n\n"
            "ÖNEMLİ MAĞAZA VE ÜRÜN YÖNLENDİRME KURALLARI:\n"
            f"1. Kullanıcı gübre, vitamin veya bitki besini hakkında soru sorarsa, yanıtının sonuna şu linki ekle: "
            f"'Kaliteli bitki gübresi ve besin çeşitlerimiz için mağazamızı ziyaret edebilirsiniz: {FERTILIZER_LINK}'\n"
            f"2. Kullanıcı saksı, saksı değişimi veya saksı boyutu sorarsa, yanıtının sonuna şu linki ekle: "
            f"'Bitkinize en uygun şık saksı modellerimiz için: {POT_LINK}'\n"
            f"3. Kullanıcı toprak, toprak değişimi veya torf hakkında soru sorarsa, yanıtının sonuna şu linki ekle: "
            f"'Zengin içerikli bitki topraklarımız için: {SOIL_LINK}'\n"
            f"4. Kullanıcı genel olarak diğer bakım malzemelerini sorarsa, genel mağaza linkimizi öner: www.{SHOP_ADDRESS}\n\n"
            f"{history_str}"
            f"Soru: {question}\nCevap:"
        )
    else:
        prompt_with_system = (
            "You are a helpful botanical assistant specializing in indoor plants. "
            "Only answer questions related to houseplants, plant care, watering, soil, fertilizing, and agricultural topics. "
            "Strictly refuse to answer unrelated questions and politely state that you can only help with plant-related queries.\n\n"
            "Respond shortly, clearly, and practically in English.\n\n"
            "IMPORTANT STORE AND PRODUCT RECOMMENDATION RULES:\n"
            f"1. If the user asks about fertilizer, vitamin, or plant nutrients, append this link at the end of the response: "
            f"'You can visit our store for high-quality plant fertilizers and nutrients: {FERTILIZER_LINK}'\n"
            f"2. If the user asks about pots, repotting, or pot size, append this link at the end of the response: "
            f"'For stylish plant pot models suitable for your plant: {POT_LINK}'\n"
            f"3. If the user asks about soil, soil change, or peat, append this link at the end of the response: "
            f"'For rich plant soil mixtures: {SOIL_LINK}'\n"
            f"4. If the user asks about other plant care materials, suggest our main store link: www.{SHOP_ADDRESS}\n\n"
            f"{history_str}"
            f"Question: {question}\nAnswer:"
        )
    payload = {
        "model": "gemma2:2b", # Default lightweight model
        "prompt": prompt_with_system,
        "stream": True
    }
    
    try:
        request_data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url, 
            data=request_data, 
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            # Clear the thinking message
            sys.stdout.write("\r" + " " * len(thinking_msg) + "\r")
            sys.stdout.write(f"{LANG_STRINGS[active_lang]['ai_prefix']}")
            sys.stdout.flush()
            
            full_response = ""
            for line in response:
                if line:
                    chunk = json.loads(line.decode("utf-8"))
                    token = chunk.get("response", "")
                    full_response += token
                    # Use global safe_print (which overrides print) to handle characters safely
                    print(token, end="", flush=True)
            print() # Final newline after response completes
            return full_response
    except urllib.error.URLError:
        sys.stdout.write("\r" + " " * len(thinking_msg) + "\r")
        sys.stdout.flush()
        return LANG_STRINGS[lang]['ai_offline']
    except Exception as e:
        sys.stdout.write("\r" + " " * len(thinking_msg) + "\r")
        sys.stdout.flush()
        return LANG_STRINGS[lang]['ai_error'].format(error=e)

def load_model(lang):
    # Load the trained machine learning model and vectorizer
    try:
        model = joblib.load('model.joblib')
        vectorizer = joblib.load('vectorizer.joblib')
        return model, vectorizer
    except FileNotFoundError:
        print(LANG_STRINGS[lang]['model_not_found'])
        sys.exit(1)

def ask_expert(question, lang):
    # Forward the question to the expert via TCP socket when the bot gets stuck
    print(f"\n{LANG_STRINGS[lang]['system_prefix']} {LANG_STRINGS[lang]['ask_expert_msg']}")
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('localhost', 5000))
        client_socket.sendall(question.encode('utf-8'))
        
        answer = client_socket.recv(1024).decode('utf-8')
        client_socket.close()
        return answer
    except ConnectionRefusedError:
        return LANG_STRINGS[lang]['expert_offline']
    except Exception as error:
        return LANG_STRINGS[lang]['expert_error'].format(error=error)

def find_answer(question, model, vectorizer):
    # Vectorize the user input
    vector = vectorizer.transform([question.lower()])
    
    # If no words overlap with the training set (TF-IDF vector is all zeros), return unknown
    if vector.nnz == 0:
        return "unknown", 0.0
    
    # Predict the closest category
    predicted_category = model.predict(vector)[0]
    
    # Retrieve the prediction confidence score
    probabilities = model.predict_proba(vector)[0]
    classes = model.classes_
    index = list(classes).index(predicted_category)
    score = probabilities[index] * 100 # Convert to percentage
    
    return predicted_category, score

def main():
    mode, lang = parse_arguments()
    knowledge_base = load_knowledge_base(lang)
    
    # Load the machine learning model
    model, vectorizer = load_model(lang)
    
    strings = LANG_STRINGS[lang]
    
    print(strings['welcome_border'])
    print(strings['welcome_title']) 
    print(strings['welcome_warning'])
    print(strings['welcome_consult'])
    print(strings['active_mode'].format(mode=mode.upper()))
    print(strings['exit_instruction'])
    print(strings['welcome_border'])
    
    # Set the confidence threshold score
    THRESHOLD = 35.0
    
    # Initialize chat history for the AI memory
    chat_history = []
    
    # Start the interactive chat loop
    while True:
        user_input = input(f"\n{strings['user_prompt']}")
        if user_input.lower() in ['çıkış', 'kapat', 'exit', 'quit', 'cikis']:
            print(strings['exit_message'])
            break
            
        # 1. Route directly to expert in HITL mode (bypassing all ML classifications and guardrails)
        if mode == 'hitl':
            answer = ask_expert(user_input, lang)
            print(f"{strings['expert_prefix']}{answer}")
            continue

        # 2. Route directly to expert in HOTL mode if expert is needed (has risk words or requests expert)
        elif mode == 'hotl':
            risk_words = ["böcek", "çürüme", "mantar", "hastalık", "kurt", "ölüyor"]
            expert_keywords = ["uzman", "expert", "operatör", "operator", "insan", "human", "bağlan", "baglan", "görüş", "gorus", "destek"]
            
            has_risk = any(word in user_input.lower() for word in risk_words)
            wants_expert = any(word in user_input.lower() for word in expert_keywords)
            
            if has_risk or wants_expert:
                if has_risk:
                    print(f"{strings['bot_prefix']}{strings['risk_detected']}")
                expert_response = ask_expert(user_input, lang)
                print(f"{strings['expert_prefix']}{expert_response}")
                continue

        # 3. For HOOTL mode or normal HOTL flow, run ML Classification
        best_key, score = find_answer(user_input, model, vectorizer)
        
        # 4. Check Guardrails for Unrelated Queries
        is_unrelated = (best_key in ['unrelated', 'unknown'] or score < THRESHOLD) and not is_plant_related(user_input)
        if is_unrelated:
            detected_lang = detect_language(user_input)
            active_lang = detected_lang if detected_lang else lang
            print(f"{LANG_STRINGS[active_lang]['bot_prefix']}{LANG_STRINGS[active_lang]['unrelated_response']}")
            continue

        # 5. Reply using local knowledge base if score is above threshold and key is valid
        if score >= THRESHOLD and best_key in knowledge_base:
            print(strings['bot_did_you_mean'].format(key=best_key, score=score))
            ans = knowledge_base[best_key]
            print(f"{strings['bot_prefix']}{ans}")
            chat_history.append((user_input, ans))
        else:
            # 6. Fallback to Local LLM (Ollama)
            ai_response = ask_local_ai(user_input, lang, chat_history)
            
            # If local LLM server is offline, fallback to expert ONLY in HOTL mode
            if "[Sistem Hatası]" in ai_response or "[System Error]" in ai_response:
                if mode == 'hotl':
                    print(f"{strings['bot_prefix']}{strings['ai_offline_fallback']}")
                    expert_response = ask_expert(user_input, lang)
                    print(f"{strings['expert_prefix']}{expert_response}")
                else:
                    print(f"{strings['ai_prefix']}{ai_response}")
            else:
                chat_history.append((user_input, ai_response))
                    
        # Limit history length to the last 4 turns (sliding window) to prevent context drift
        if len(chat_history) > 4:
            chat_history.pop(0)

if __name__ == "__main__":
    main()