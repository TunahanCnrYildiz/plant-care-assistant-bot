import sys
import time
import socket
import os
import joblib
import json
import urllib.request
import threading
import uuid
import queue
from flask import Flask, request, Response, render_template, stream_with_context

app = Flask(__name__, template_folder='templates', static_folder='static')

# Translation dictionary for internationalization (i18n)
LANG_STRINGS = {
    'tr': {
        'system_prefix': '[Sistem]',
        'ai_generating': 'Yerel yapay zeka (Ollama) yanıt üretiyor. Lütfen bekleyin...',
        'ai_offline': '[Sistem Hatası] Ollama sunucusuna ulaşılamadı. Lütfen Ollama uygulamasının açık olduğundan emin olun.',
        'ai_error': '[Sistem Hatası] Yapay zeka ile haberleşirken hata oluştu: {error}',
        'model_not_found': '[Hata] Eğitilmiş model dosyaları bulunamadı. Lütfen önce train.py dosyasını çalıştırın.',
        'knowledge_base_not_found': 'Hata: knowledge.txt dosyası bulunamadı.',
        'bot_did_you_mean': "Bunu mu demek istediniz: '<strong>{key}</strong>'? (Güven Skoru: %{score:.2f})",
        'risk_detected': 'Mesajınızda bitkiniz için riskli olabilecek bir durum tespit ettim.',
        'ai_offline_fallback': 'Yerel yapay zeka sunucusuna bağlanılamadı. Uzmana aktarılıyorsunuz...',
        'ask_expert_msg': 'İMDAT! Uzmana bağlanılıyor. Lütfen bekleyin...',
        'expert_offline': '[Sistem Hatası] Uzmana ulaşılamıyor. Lütfen expert.py\'nin çalıştığından emin olun.',
        'expert_error': '[Sistem Hatası] Beklenmeyen bir hata oluştu: {error}',
        'bot_prefix': 'Bot: ',
        'expert_prefix': 'Botanik Uzmanı: ',
        'ai_prefix': 'Yapay Zeka Asistanı: ',
        'unrelated_response': "Ben sadece bitki bakımı, toprak, sulama, gübreleme ve zirai konularla ilgili sorulara cevap vereebilirim. Lütfen bitkilerinizle ilgili bir soru sorunuz.",
        'expert_ended': 'Sohbet oturumu uzman tarafından sonlandırılmıştır.'
    },
    'en': {
        'system_prefix': '[System]',
        'ai_generating': 'Local AI (Ollama) is generating response. Please wait...',
        'ai_offline': '[System Error] Ollama server could not be reached. Please ensure the Ollama application is running.',
        'ai_error': '[System Error] An error occurred while communicating with AI: {error}',
        'model_not_found': '[Error] Trained model files not found. Please run train.py first.',
        'knowledge_base_not_found': 'Error: knowledge.txt file not found.',
        'bot_did_you_mean': "Did you mean: '<strong>{key}</strong>'? (Confidence Score: %{score:.2f})",
        'risk_detected': 'I detected a potentially risky condition for your plant in your message.',
        'ai_offline_fallback': 'Local AI server could not be reached. Transferring you to the expert...',
        'ask_expert_msg': 'SOS! Connecting to expert. Please wait...',
        'expert_offline': '[System Error] Expert cannot be reached. Please ensure expert.py is running.',
        'expert_error': '[System Error] An unexpected error occurred: {error}',
        'bot_prefix': 'Bot: ',
        'expert_prefix': 'Botanist Expert: ',
        'ai_prefix': 'AI Assistant: ',
        'unrelated_response': "I can only answer questions related to plant care, soil, watering, fertilizing, and agricultural topics. Please ask a question about your plants.",
        'expert_ended': 'The chat session has been terminated by the expert.'
    }
}

# Threshold configuration
THRESHOLD = 35.0

# Thread-safe Active Chats Registry
# session_id -> { session_id, question_history: list, current_user_message, current_expert_answer, user_event, timestamp, lang }
active_chats = {}
active_chats_lock = threading.Lock()

# Thread-safe Closed Chats Registry (to notify user on next message if expert closed session)
closed_sessions = {}
closed_sessions_lock = threading.Lock()

# Thread-safe Expert Stream Queues (for broadcasting events to expert panels)
expert_queues = []
expert_queues_lock = threading.Lock()

# Load Model and Vectorizer globally
try:
    model = joblib.load('model.joblib')
    vectorizer = joblib.load('vectorizer.joblib')
except FileNotFoundError:
    print("Error: model.joblib or vectorizer.joblib not found. Please run train.py first.")
    sys.exit(1)

# Load Knowledge Base
def load_knowledge_base():
    knowledge_base = {}
    try:
        with open('knowledge.txt', 'r', encoding='utf-8') as f:
            for line in f:
                if '|' in line:
                    key, value = line.strip().split('|', 1)
                    knowledge_base[key] = value
    except FileNotFoundError:
        print("Error: knowledge.txt not found.")
    return knowledge_base

knowledge_base = load_knowledge_base()

def notify_expert_listeners_new(session_id, question, lang):
    with expert_queues_lock:
        for q in expert_queues:
            q.put({
                "type": "new_case",
                "session_id": session_id,
                "question": question,
                "lang": lang,
                "timestamp": time.time()
            })

def notify_expert_listeners_update(session_id, question):
    with expert_queues_lock:
        for q in expert_queues:
            q.put({
                "type": "new_message",
                "session_id": session_id,
                "question": question
            })

def notify_expert_listeners_close(session_id):
    with expert_queues_lock:
        for q in expert_queues:
            q.put({
                "type": "session_closed",
                "session_id": session_id
            })

def detect_language(text):
    text_lower = text.lower()
    
    # 1. Turkish specific characters
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
    import re
    words = set(re.findall(r'\b\w+\b', text_lower))
    
    exact_terms = {
        "bitki", "bitkim", "bitkinin", "bitkiler", "bitkisi", "bitkilerim",
        "çiçek", "çiçeğim", "çiçeğin", "çiçekler", "çiçeği", "cicek", "cicegim",
        "yaprak", "yaprağım", "yaprağın", "yapraklar", "yaprağı", "yaprakları", "yapragı",
        "kök", "kökler", "köku", "kökleri", "kok", "kokler",
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
    
    if words.intersection(exact_terms):
        return True
        
    stems = ["sarar", "sararm", "sarari", "kuruyor", "kurum", "kurudu", "kurus", "soldu", "soluyor", "solma", "dökül", "dokul", "çürü", "curu", "yetiş", "yetis"]
    for stem in stems:
        for word in words:
            if word.startswith(stem):
                return True
                
    return False

def ask_expert(question, lang):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(3)
        client_socket.connect(('localhost', 5000))
        client_socket.sendall(question.encode('utf-8'))
        answer = client_socket.recv(1024).decode('utf-8')
        client_socket.close()
        return answer
    except Exception:
        return "[Sistem Hatası] Uzmana ulaşılamıyor."

def find_answer(question, model, vectorizer):
    vector = vectorizer.transform([question.lower()])
    if vector.nnz == 0:
        return "unknown", 0.0
    predicted_category = model.predict(vector)[0]
    probabilities = model.predict_proba(vector)[0]
    classes = model.classes_
    index = list(classes).index(predicted_category)
    score = probabilities[index] * 100
    return predicted_category, score

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/expert')
def expert_panel_page():
    return render_template('expert.html')

@app.route('/api/expert/stream')
def expert_stream():
    def stream():
        q = queue.Queue()
        with expert_queues_lock:
            expert_queues.append(q)
        try:
            # 1. Send existing active chats on connection
            with active_chats_lock:
                for session_id, chat in active_chats.items():
                    yield "data: {}\n\n".format(json.dumps({
                        "type": "new_case",
                        "session_id": session_id,
                        "question": chat["question_history"][0]["content"] if chat["question_history"] else "",
                        "history": chat["question_history"],
                        "lang": chat["lang"],
                        "timestamp": chat["timestamp"]
                    }))
            
            # 2. Yield events pushed to the queue
            while True:
                try:
                    item = q.get(timeout=20)
                    yield "data: {}\n\n".format(json.dumps(item))
                except queue.Empty:
                    # Keep-alive PING
                    yield "data: [PING]\n\n"
        finally:
            with expert_queues_lock:
                if q in expert_queues:
                    expert_queues.remove(q)
    return Response(stream(), content_type='text/event-stream')

@app.route('/api/expert/answer', methods=['POST'])
def expert_answer():
    data = request.json or {}
    session_id = data.get('session_id')
    answer = data.get('answer', '').strip()
    
    if not session_id or not answer:
        return {"error": "Missing session_id or answer"}, 400
        
    with active_chats_lock:
        if session_id in active_chats:
            active_chats[session_id]['current_expert_answer'] = answer
            active_chats[session_id]['user_event'].set()
            return {"status": "success"}
        else:
            return {"error": "Session not found"}, 404

@app.route('/api/expert/close', methods=['POST'])
def expert_close():
    data = request.json or {}
    session_id = data.get('session_id')
    
    if not session_id:
        return {"error": "Missing session_id"}, 400
        
    with active_chats_lock:
        if session_id in active_chats:
            lang = active_chats[session_id].get('lang', 'tr')
            closing_msg = LANG_STRINGS[lang]['expert_ended']
            
            # Wake up user blocked thread if waiting with a closing message
            active_chats[session_id]['current_expert_answer'] = closing_msg
            active_chats[session_id]['user_event'].set()
            active_chats.pop(session_id, None)
            
            # Save to closed_sessions to notify user on their next message if they were not waiting
            with closed_sessions_lock:
                closed_sessions[session_id] = closing_msg
                
            notify_expert_listeners_close(session_id)
            return {"status": "success"}
        else:
            return {"error": "Session not found"}, 404

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json or {}
    user_input = data.get('message', '').strip()
    mode = data.get('mode', 'hootl').lower()
    lang = data.get('lang', 'tr').lower()
    chat_history = data.get('history', [])
    session_id = data.get('session_id', 'default_session')

    if not user_input:
        return Response("data: {}\n\n".format(json.dumps({"type": "error", "content": "Empty prompt"})), content_type='text/event-stream')

    # Check if this session was recently closed by the expert
    was_closed = False
    closing_msg = ""
    with closed_sessions_lock:
        if session_id in closed_sessions:
            was_closed = True
            closing_msg = closed_sessions.pop(session_id)

    if was_closed:
        def closed_stream():
            yield f"data: {json.dumps({'type': 'expert_response', 'content': closing_msg, 'prefix': LANG_STRINGS[lang]['system_prefix']})}\n\n"
            yield "data: [DONE]\n\n"
        return Response(stream_with_context(closed_stream()), content_type='text/event-stream')

    # A. Check if the session is already active in expert chat mode
    in_expert_chat = False
    with active_chats_lock:
        if session_id in active_chats:
            in_expert_chat = True
            chat_session = active_chats[session_id]

    if in_expert_chat:
        def chat_stream():
            # Process user message in the active session
            with active_chats_lock:
                chat_session['current_user_message'] = user_input
                chat_session['question_history'].append({"role": "user", "content": user_input})
                chat_session['current_expert_answer'] = None
                chat_session['user_event'].clear()
            
            # Notify expert dashboard
            notify_expert_listeners_update(session_id, user_input)
            
            # Block waiting for response
            success = chat_session['user_event'].wait(timeout=60.0)
            
            with active_chats_lock:
                ans = chat_session['current_expert_answer'] if success else None
                if ans:
                    chat_session['question_history'].append({"role": "expert", "content": ans})
                else:
                    # Timeout cleanup
                    active_chats.pop(session_id, None)
                    notify_expert_listeners_close(session_id)
                    ans = "Uzmandan yanıt alınamadı. Sohbet sonlandırıldı."
            
            yield f"data: {json.dumps({'type': 'expert_response', 'content': ans, 'prefix': LANG_STRINGS[lang]['expert_prefix']})}\n\n"
            yield "data: [DONE]\n\n"
            
        return Response(stream_with_context(chat_stream()), content_type='text/event-stream')

    # B. If not in active expert chat, perform normal classification flow
    def event_stream():
        # 1. Route directly to expert in HITL mode (bypassing all ML classifications and guardrails)
        if mode == 'hitl':
            yield f"data: {json.dumps({'type': 'status', 'content': LANG_STRINGS[lang]['ask_expert_msg'], 'prefix': LANG_STRINGS[lang]['system_prefix']})}\n\n"
            
            # Initialize persistent chat session
            event = threading.Event()
            with active_chats_lock:
                active_chats[session_id] = {
                    "session_id": session_id,
                    "question_history": [{"role": "user", "content": user_input}],
                    "current_user_message": user_input,
                    "current_expert_answer": None,
                    "user_event": event,
                    "timestamp": time.time(),
                    "lang": lang
                }
            notify_expert_listeners_new(session_id, user_input, lang)
            
            # Block waiting for first reply
            success = event.wait(timeout=60.0)
            
            with active_chats_lock:
                if success and session_id in active_chats:
                    ans = active_chats[session_id]['current_expert_answer']
                    if ans:
                        active_chats[session_id]['question_history'].append({"role": "expert", "content": ans})
                else:
                    active_chats.pop(session_id, None)
                    notify_expert_listeners_close(session_id)
                    # Fallback to expert socket
                    ans = ask_expert(user_input, lang)
                    if "[Sistem Hatası]" in ans or "[System Error]" in ans:
                        if lang == 'tr':
                            ans = "Şu anda aktif bir uzman bulunmuyor. Lütfen daha sonra tekrar deneyin."
                        else:
                            ans = "Currently no experts are active. Please try again later."
                            
            yield f"data: {json.dumps({'type': 'expert_response', 'content': ans, 'prefix': LANG_STRINGS[lang]['expert_prefix']})}\n\n"
            yield "data: [DONE]\n\n"
            return
            
        # 2. Route directly to expert in HOTL mode if expert is needed (has risk words or requests expert)
        elif mode == 'hotl':
            risk_words = ["böcek", "çürüme", "mantar", "hastalık", "kurt", "ölüyor"]
            expert_keywords = ["uzman", "expert", "operatör", "operator", "insan", "human", "bağlan", "baglan", "görüş", "gorus", "destek"]
            
            has_risk = any(word in user_input.lower() for word in risk_words)
            wants_expert = any(word in user_input.lower() for word in expert_keywords)
            
            if has_risk or wants_expert:
                if has_risk:
                    yield f"data: {json.dumps({'type': 'status', 'content': LANG_STRINGS[lang]['risk_detected'], 'prefix': LANG_STRINGS[lang]['bot_prefix']})}\n\n"
                yield f"data: {json.dumps({'type': 'status', 'content': LANG_STRINGS[lang]['ask_expert_msg'], 'prefix': LANG_STRINGS[lang]['system_prefix']})}\n\n"
                
                # Initialize persistent chat session
                event = threading.Event()
                with active_chats_lock:
                    active_chats[session_id] = {
                        "session_id": session_id,
                        "question_history": [{"role": "user", "content": user_input}],
                        "current_user_message": user_input,
                        "current_expert_answer": None,
                        "user_event": event,
                        "timestamp": time.time(),
                        "lang": lang
                    }
                notify_expert_listeners_new(session_id, user_input, lang)
                
                success = event.wait(timeout=60.0)
                
                with active_chats_lock:
                    if success and session_id in active_chats:
                        ans = active_chats[session_id]['current_expert_answer']
                        if ans:
                            active_chats[session_id]['question_history'].append({"role": "expert", "content": ans})
                    else:
                        active_chats.pop(session_id, None)
                        notify_expert_listeners_close(session_id)
                        # Fallback to expert socket
                        ans = ask_expert(user_input, lang)
                        if "[Sistem Hatası]" in ans or "[System Error]" in ans:
                            if lang == 'tr':
                                ans = "Şu anda aktif bir uzman bulunmuyor. Lütfen daha sonra tekrar deneyin."
                            else:
                                ans = "Currently no experts are active. Please try again later."
                                
                yield f"data: {json.dumps({'type': 'expert_response', 'content': ans, 'prefix': LANG_STRINGS[lang]['expert_prefix']})}\n\n"
                yield "data: [DONE]\n\n"
                return

        # 3. For HOOTL mode or normal HOTL flow, run ML Classification
        best_key, score = find_answer(user_input, model, vectorizer)
        
        # 4. Check Guardrails for Unrelated Queries
        is_unrelated = (best_key in ['unrelated', 'unknown'] or score < THRESHOLD) and not is_plant_related(user_input)
        if is_unrelated:
            detected_lang = detect_language(user_input)
            active_lang = detected_lang if detected_lang else lang
            unrelated_msg = LANG_STRINGS[active_lang]['unrelated_response']
            yield f"data: {json.dumps({'type': 'unrelated', 'content': unrelated_msg, 'lang': active_lang})}\n\n"
            yield "data: [DONE]\n\n"
            return

        # 4. If Database Category Match
        if score >= THRESHOLD and best_key in knowledge_base:
            ans = knowledge_base[best_key]
            did_you_mean = LANG_STRINGS[lang]['bot_did_you_mean'].format(key=best_key, score=score)
            
            # Format store recommendation links if matched in answer
            SHOP_ADDRESS = "[SITENIZ.COM]"
            FERTILIZER_LINK = f"www.{SHOP_ADDRESS}/gubreler"
            POT_LINK = f"www.{SHOP_ADDRESS}/saksilar"
            SOIL_LINK = f"www.{SHOP_ADDRESS}/topraklar"
            
            recommendation = None
            if best_key in ['fertilizer']:
                recommendation = f"Kaliteli bitki gübresi ve besin çeşitlerimiz için mağazamızı ziyaret edebilirsiniz: <a href='https://{FERTILIZER_LINK}' target='_blank' class='rich-link'>{FERTILIZER_LINK}</a>"
            elif best_key in ['pot']:
                recommendation = f"Bitkinize en uygun şık saksı modellerimiz için: <a href='https://{POT_LINK}' target='_blank' class='rich-link'>{POT_LINK}</a>"
            elif best_key in ['dry', 'water']:
                recommendation = f"Zengin içerikli bitki topraklarımız için: <a href='https://{SOIL_LINK}' target='_blank' class='rich-link'>{SOIL_LINK}</a>"
                
            yield f"data: {json.dumps({'type': 'db', 'content': ans, 'did_you_mean': did_you_mean, 'prefix': LANG_STRINGS[lang]['bot_prefix'], 'recommendation': recommendation})}\n\n"
            yield "data: [DONE]\n\n"
            return

        # 5. Fallback to Local LLM (Ollama)
        detected_lang = detect_language(user_input)
        active_lang = detected_lang if detected_lang else lang

        # Format sliding window conversation history
        history_str = ""
        if chat_history:
            if active_lang == 'tr':
                history_str = "KONUŞMA GEÇMİŞİ (BAĞLAM):\n"
                for turn in chat_history[-4:]:  # last 4 turns
                    history_str += f"Soru: {turn.get('user', '')}\nCevap: {turn.get('assistant', '')}\n"
                history_str += "\n"
            else:
                history_str = "CONVERSATION HISTORY (CONTEXT):\n"
                for turn in chat_history[-4:]:  # last 4 turns
                    history_str += f"Question: {turn.get('user', '')}\nAnswer: {turn.get('assistant', '')}\n"
                history_str += "\n"

        SHOP_ADDRESS = "[SITENIZ.COM]"
        FERTILIZER_LINK = f"www.{SHOP_ADDRESS}/gubreler"
        POT_LINK = f"www.{SHOP_ADDRESS}/saksilar"
        SOIL_LINK = f"www.{SHOP_ADDRESS}/topraklar"

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
                f"Soru: {user_input}\nCevap:"
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
                f"Question: {user_input}\nAnswer:"
            )

        payload = {
            "model": "gemma2:2b",
            "prompt": prompt_with_system,
            "stream": True
        }
        
        url = "http://localhost:11434/api/generate"
        
        try:
            request_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url, 
                data=request_data, 
                headers={"Content-Type": "application/json"}
            )
            # Send status update that AI is thinking
            thinking_msg = f"{LANG_STRINGS[active_lang]['ai_prefix'].strip()} is thinking..." if active_lang == 'en' else f"{LANG_STRINGS[active_lang]['ai_prefix'].strip()} düşünüyor..."
            yield f"data: {json.dumps({'type': 'status', 'content': thinking_msg, 'prefix': LANG_STRINGS[active_lang]['system_prefix']})}\n\n"
            
            with urllib.request.urlopen(req, timeout=15) as response:
                yield f"data: {json.dumps({'type': 'ai_start', 'prefix': LANG_STRINGS[active_lang]['ai_prefix']})}\n\n"
                for line in response:
                    if line:
                        chunk = json.loads(line.decode("utf-8"))
                        token = chunk.get("response", "")
                        yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            yield "data: [DONE]\n\n"
        except urllib.error.URLError:
            if mode == 'hotl':
                # Fallback to expert panel if local LLM is offline
                yield f"data: {json.dumps({'type': 'status', 'content': LANG_STRINGS[lang]['ai_offline_fallback'], 'prefix': LANG_STRINGS[lang]['bot_prefix']})}\n\n"
                
                # Initialize persistent chat session
                event = threading.Event()
                with active_chats_lock:
                    active_chats[session_id] = {
                        "session_id": session_id,
                        "question_history": [{"role": "user", "content": user_input}],
                        "current_user_message": user_input,
                        "current_expert_answer": None,
                        "user_event": event,
                        "timestamp": time.time(),
                        "lang": lang
                    }
                notify_expert_listeners_new(session_id, user_input, lang)
                
                # Block waiting for first reply
                success = event.wait(timeout=60.0)
                
                with active_chats_lock:
                    if success and session_id in active_chats:
                        ans = active_chats[session_id]['current_expert_answer']
                        if ans:
                            active_chats[session_id]['question_history'].append({"role": "expert", "content": ans})
                    else:
                        active_chats.pop(session_id, None)
                        notify_expert_listeners_close(session_id)
                        # Fallback to expert socket
                        ans = ask_expert(user_input, lang)
                        if "[Sistem Hatası]" in ans or "[System Error]" in ans:
                            if lang == 'tr':
                                ans = "Şu anda aktif bir uzman bulunmuyor. Lütfen daha sonra tekrar deneyin."
                            else:
                                ans = "Currently no experts are active. Please try again later."
                                
                yield f"data: {json.dumps({'type': 'expert_response', 'content': ans, 'prefix': LANG_STRINGS[lang]['expert_prefix']})}\n\n"
                yield "data: [DONE]\n\n"
            else:
                # In HOOTL mode, just show the offline error and do not connect to expert
                yield f"data: {json.dumps({'type': 'error', 'content': LANG_STRINGS[lang]['ai_offline']})}\n\n"
                yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': LANG_STRINGS[lang]['ai_error'].format(error=str(e))})}\n\n"
            yield "data: [DONE]\n\n"

    return Response(stream_with_context(event_stream()), content_type='text/event-stream')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)
